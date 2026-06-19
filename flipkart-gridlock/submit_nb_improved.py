"""Improved version of the 90.96 notebook. Same pipeline + two robust, transferable
gains validated on the Day-49 holdout (0.9317 -> ~0.941):
  1. sample weight 1 + 5*demand  (focus the fit on high-demand Highway/Street rows
     that drive R²; the notebook's RMSE was dominated by 88% low-demand rows)
  2. 7-seed ensemble             (variance reduction)
Depth stays at 6 (proven on LB; deeper only helped the morning-optimistic holdout
by ~0.001 and capacity bumps have misled us on the real daytime test before).
Writes submissions/sub_nb_improved.csv. Does not touch other files.
"""
import numpy as np, pandas as pd, pygeohash as pgh
from xgboost import XGBRegressor
from sklearn.model_selection import train_test_split

N_SEEDS = 7
WEXP = 5.0

train = pd.read_csv('dataset/train.csv')
test = pd.read_csv('dataset/test.csv')
test_index = test['Index'].copy()

def gstats_from(df):
    g = df.groupby('geohash')['demand'].agg(geohash_mean='mean', geohash_std='std').reset_index()
    g['geohash_std'] = g['geohash_std'].fillna(0)
    return g

def engineer(df, gs):
    df = df.copy()
    df[['hour','minute']] = df['timestamp'].str.split(':', expand=True).astype(int)
    df['time_of_day'] = df['hour']*60 + df['minute']
    df['hour_sin'] = np.sin(2*np.pi*df['hour']/24); df['hour_cos'] = np.cos(2*np.pi*df['hour']/24)
    df['is_peak'] = df['hour'].isin([7,8,9,17,18,19]).astype(int)
    df['lat'] = df['geohash'].apply(lambda x: pgh.decode(x)[0])
    df['lon'] = df['geohash'].apply(lambda x: pgh.decode(x)[1])
    df = df.merge(gs, on='geohash', how='left')
    gm = gs['geohash_mean'].mean()
    df['geohash_mean'] = df['geohash_mean'].fillna(gm); df['geohash_std'] = df['geohash_std'].fillna(0)
    df['lanes_x_highway'] = df['NumberofLanes']*(df['RoadType']=='Highway').astype(int)
    df['Temperature'] = df['Temperature'].fillna(df['Temperature'].median())
    df['Weather'] = df['Weather'].fillna('Sunny'); df['RoadType'] = df['RoadType'].fillna('Residential')
    df = pd.get_dummies(df, columns=['RoadType','LargeVehicles','Landmarks','Weather'], drop_first=True)
    return df

gs = gstats_from(train)                       # geohash stats over BOTH days (notebook behaviour)
train_fe = engineer(train, gs); test_fe = engineer(test, gs)
X = train_fe.drop(['demand','Index','geohash','timestamp'], axis=1, errors='ignore')
y = train_fe['demand'].values
Xte = test_fe.drop(['Index','geohash','timestamp'], axis=1, errors='ignore').reindex(columns=X.columns, fill_value=0)

def xgb(seed):
    return XGBRegressor(n_estimators=2000, learning_rate=0.05, max_depth=6, subsample=0.8,
        colsample_bytree=0.8, min_child_weight=3, reg_alpha=0.1, reg_lambda=1.0,
        early_stopping_rounds=50, tree_method='hist', device='cpu', random_state=seed)

preds = np.zeros(len(Xte))
for s in range(N_SEEDS):
    Xt, Xv, yt, yv = train_test_split(X, y, test_size=0.2, random_state=s)
    m = xgb(s); m.fit(Xt, yt, sample_weight=1+WEXP*yt, eval_set=[(Xv, yv)], verbose=False)
    preds += np.clip(m.predict(Xte), 0, 1)
preds /= N_SEEDS

out = pd.DataFrame({'Index': test_index, 'demand': preds})
assert out.shape == (41778, 2) and list(out.columns) == ['Index','demand']
assert np.isfinite(out['demand']).all() and ((out['demand']>=0)&(out['demand']<=1)).all()
out.to_csv('submissions/sub_nb_improved.csv', index=False)
print(f"wrote submissions/sub_nb_improved.csv  mean={preds.mean():.4f} min={preds.min():.4f} max={preds.max():.4f}")
