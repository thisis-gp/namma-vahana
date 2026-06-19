"""Reproduce the 90.96 notebook pipeline and test stacking our validated gains.
Evaluation: Day-49 morning holdout (the LB-correlated proxy), with geohash stats
computed ONLY on the training portion (no leak)."""
import numpy as np, pandas as pd, pygeohash as pgh
from xgboost import XGBRegressor
from sklearn.metrics import r2_score

train = pd.read_csv('dataset/train.csv')

def engineer(df, gstats=None):
    df = df.copy()
    df[['hour','minute']] = df['timestamp'].str.split(':', expand=True).astype(int)
    df['time_of_day'] = df['hour']*60 + df['minute']
    df['hour_sin'] = np.sin(2*np.pi*df['hour']/24); df['hour_cos'] = np.cos(2*np.pi*df['hour']/24)
    df['is_peak'] = df['hour'].isin([7,8,9,17,18,19]).astype(int)
    df['lat'] = df['geohash'].apply(lambda x: pgh.decode(x)[0])
    df['lon'] = df['geohash'].apply(lambda x: pgh.decode(x)[1])
    df = df.merge(gstats, on='geohash', how='left')
    gm = gstats['geohash_mean'].mean()
    df['geohash_mean'] = df['geohash_mean'].fillna(gm); df['geohash_std'] = df['geohash_std'].fillna(0)
    df['lanes_x_highway'] = df['NumberofLanes']*(df['RoadType']=='Highway').astype(int)
    df['Temperature'] = df['Temperature'].fillna(df['Temperature'].median())
    df['Weather'] = df['Weather'].fillna('Sunny'); df['RoadType'] = df['RoadType'].fillna('Residential')
    df = pd.get_dummies(df, columns=['RoadType','LargeVehicles','Landmarks','Weather'], drop_first=True)
    return df

def gstats_from(df):
    g = df.groupby('geohash')['demand'].agg(geohash_mean='mean', geohash_std='std').reset_index()
    g['geohash_std'] = g['geohash_std'].fillna(0); return g

def model(weight=False, seed=42):
    return XGBRegressor(n_estimators=2000, learning_rate=0.05, max_depth=6, subsample=0.8,
        colsample_bytree=0.8, min_child_weight=3, reg_alpha=0.1, reg_lambda=1.0,
        early_stopping_rounds=50, tree_method='hist', device='cpu', random_state=seed)

d48 = train[train.day==48]; d49 = train[train.day==49].reset_index(drop=True)
DROP = ['demand','Index','geohash','timestamp']

def evaluate(label, weight=False, n_seeds=1, extra=None):
    rng = np.random.RandomState(0); mask = rng.rand(len(d49))<0.5
    tr_raw = pd.concat([d48, d49[mask]], ignore_index=True)
    ho_raw = d49[~mask].reset_index(drop=True)
    gs = gstats_from(tr_raw)
    trf = engineer(tr_raw, gs); hof = engineer(ho_raw, gs)
    if extra: trf, hof = extra(trf, hof, tr_raw, ho_raw)
    X = trf.drop([c for c in DROP if c in trf], axis=1); y = trf['demand'].values
    Xh = hof.reindex(columns=X.columns, fill_value=0); yh = hof['demand'].values
    w = (1+3*y) if weight else None
    # early stop on a slice of train (mirrors notebook's random valid)
    from sklearn.model_selection import train_test_split
    preds = np.zeros(len(Xh))
    for s in range(n_seeds):
        Xt,Xv,yt,yv,(wt) = (*train_test_split(X,y,test_size=0.2,random_state=s), None)
        wt = (1+3*yt) if weight else None
        m = model(seed=s); m.fit(Xt,yt,sample_weight=wt,eval_set=[(Xv,yv)],verbose=False)
        preds += np.clip(m.predict(Xh),0,1)
    preds/=n_seeds
    print(f'{label:34s} D49-holdout R2={r2_score(yh,preds):.4f}')

evaluate('notebook baseline (XGB)')
evaluate('+ demand weighting', weight=True)
evaluate('+ 5-seed ensemble', n_seeds=5)
evaluate('+ weighting + 5-seed', weight=True, n_seeds=5)
