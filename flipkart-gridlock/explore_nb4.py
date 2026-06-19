"""Round 4: weight sweep, lower-lr XGB, and HistGradientBoosting diversity.
Day-49 holdout, leak-safe."""
import numpy as np, pandas as pd, pygeohash as pgh
from xgboost import XGBRegressor
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import r2_score
from sklearn.model_selection import train_test_split

train = pd.read_csv('dataset/train.csv')
d48 = train[train.day==48]; d49 = train[train.day==49].reset_index(drop=True)
rng = np.random.RandomState(0); mask = rng.rand(len(d49))<0.5
tr_raw = pd.concat([d48, d49[mask]], ignore_index=True); ho_raw = d49[~mask].reset_index(drop=True)
gstat = tr_raw.groupby('geohash')['demand'].agg(geohash_mean='mean', geohash_std='std'); gstat['geohash_std']=gstat['geohash_std'].fillna(0)
GM = gstat['geohash_mean'].mean()

def engineer(df):
    df = df.copy()
    df[['hour','minute']] = df['timestamp'].str.split(':', expand=True).astype(int)
    df['time_of_day'] = df['hour']*60 + df['minute']
    df['hour_sin'] = np.sin(2*np.pi*df['hour']/24); df['hour_cos'] = np.cos(2*np.pi*df['hour']/24)
    df['is_peak'] = df['hour'].isin([7,8,9,17,18,19]).astype(int)
    df['lat'] = df['geohash'].apply(lambda x: pgh.decode(x)[0]); df['lon'] = df['geohash'].apply(lambda x: pgh.decode(x)[1])
    df['geohash_mean'] = df['geohash'].map(gstat['geohash_mean']).fillna(GM)
    df['geohash_std']  = df['geohash'].map(gstat['geohash_std']).fillna(0)
    df['lanes_x_highway'] = df['NumberofLanes']*(df['RoadType']=='Highway').astype(int)
    df['Temperature'] = df['Temperature'].fillna(df['Temperature'].median())
    df['Weather'] = df['Weather'].fillna('Sunny'); df['RoadType'] = df['RoadType'].fillna('Residential')
    df = pd.get_dummies(df, columns=['RoadType','LargeVehicles','Landmarks','Weather'], drop_first=True)
    return df

DROP=['demand','Index','geohash','timestamp']
trf=engineer(tr_raw); hof=engineer(ho_raw)
X=trf.drop([c for c in DROP if c in trf],axis=1); y=trf['demand'].values
Xh=hof.reindex(columns=X.columns,fill_value=0); yh=hof['demand'].values

def xgb(seed, lr=0.05, depth=6, mcw=3):
    return XGBRegressor(n_estimators=4000, learning_rate=lr, max_depth=depth, subsample=0.8,
        colsample_bytree=0.8, min_child_weight=mcw, reg_alpha=0.1, reg_lambda=1.0,
        early_stopping_rounds=50, tree_method='hist', device='cpu', random_state=seed)

def run_xgb(wexp=8, n_seeds=5, lr=0.05, depth=6, mcw=3):
    preds=np.zeros(len(Xh))
    for s in range(n_seeds):
        Xt,Xv,yt,yv=train_test_split(X,y,test_size=0.2,random_state=s)
        m=xgb(s,lr,depth,mcw); m.fit(Xt,yt,sample_weight=1+wexp*yt,eval_set=[(Xv,yv)],verbose=False)
        preds+=np.clip(m.predict(Xh),0,1)
    return preds/n_seeds

def run_hgb(wexp=8, n_seeds=5):
    preds=np.zeros(len(Xh))
    for s in range(n_seeds):
        m=HistGradientBoostingRegressor(max_iter=1500, learning_rate=0.05, max_leaf_nodes=63,
            l2_regularization=1.0, validation_fraction=0.2, early_stopping=True, random_state=s)
        m.fit(X,y,sample_weight=1+wexp*y); preds+=np.clip(m.predict(Xh),0,1)
    return preds/n_seeds

xgb_base=run_xgb(wexp=8,n_seeds=5); print(f'{"XGB w8 5seed":32s} R2={r2_score(yh,xgb_base):.4f}')
for w in [10,12,16]:
    print(f'{"XGB w"+str(w)+" 5seed":32s} R2={r2_score(yh,run_xgb(wexp=w)):.4f}')
print(f'{"XGB lr0.03 w8 5seed":32s} R2={r2_score(yh,run_xgb(wexp=8,lr=0.03)):.4f}')
print(f'{"XGB mcw5 w8 5seed":32s} R2={r2_score(yh,run_xgb(wexp=8,mcw=5)):.4f}')
xgb10=run_xgb(wexp=8,n_seeds=10); print(f'{"XGB w8 10seed":32s} R2={r2_score(yh,xgb10):.4f}')
hgb=run_hgb(wexp=8,n_seeds=5); print(f'{"HGB w8 5seed (standalone)":32s} R2={r2_score(yh,hgb):.4f}')
print(f'{"BLEND 0.7 XGB + 0.3 HGB":32s} R2={r2_score(yh,0.7*xgb10+0.3*hgb):.4f}')
print(f'{"BLEND 0.85 XGB + 0.15 HGB":32s} R2={r2_score(yh,0.85*xgb10+0.15*hgb):.4f}')
