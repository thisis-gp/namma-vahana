"""Round 2: push the 90.96 notebook further. Day-49 holdout, leak-safe geohash stats."""
import numpy as np, pandas as pd, pygeohash as pgh
from xgboost import XGBRegressor
import lightgbm as lgb
from sklearn.metrics import r2_score
from sklearn.model_selection import train_test_split

train = pd.read_csv('dataset/train.csv')
d48 = train[train.day==48]; d49 = train[train.day==49].reset_index(drop=True)

def gstats_from(df):
    g = df.groupby('geohash')['demand'].agg(geohash_mean='mean', geohash_std='std').reset_index()
    g['geohash_std'] = g['geohash_std'].fillna(0)
    g5 = df.assign(g5=df.geohash.str[:5]).groupby('g5')['demand'].mean().rename('g5_mean').reset_index()
    return g, g5

def engineer(df, gs, g5s, add_g5=False):
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
    if add_g5:
        df['g5'] = df.geohash.str[:5]
        df = df.merge(g5s, on='g5', how='left'); df['g5_mean'] = df['g5_mean'].fillna(gm)
        df['geohash_mean'] = df['geohash_mean'].where(df['geohash_mean']!=gm, df['g5_mean'])
        df.drop('g5', axis=1, inplace=True)
    df['lanes_x_highway'] = df['NumberofLanes']*(df['RoadType']=='Highway').astype(int)
    df['Temperature'] = df['Temperature'].fillna(df['Temperature'].median())
    df['Weather'] = df['Weather'].fillna('Sunny'); df['RoadType'] = df['RoadType'].fillna('Residential')
    df = pd.get_dummies(df, columns=['RoadType','LargeVehicles','Landmarks','Weather'], drop_first=True)
    return df

DROP = ['demand','Index','geohash','timestamp']
def split_xy(trf, hof):
    X = trf.drop([c for c in DROP if c in trf], axis=1); y = trf['demand'].values
    Xh = hof.reindex(columns=X.columns, fill_value=0); yh = hof['demand'].values
    return X, y, Xh, yh

def xgb(seed, depth=6):
    return XGBRegressor(n_estimators=2000, learning_rate=0.05, max_depth=depth, subsample=0.8,
        colsample_bytree=0.8, min_child_weight=3, reg_alpha=0.1, reg_lambda=1.0,
        early_stopping_rounds=50, tree_method='hist', device='cpu', random_state=seed)

rng = np.random.RandomState(0); mask = rng.rand(len(d49))<0.5
tr_raw = pd.concat([d48, d49[mask]], ignore_index=True); ho_raw = d49[~mask].reset_index(drop=True)
gs, g5s = gstats_from(tr_raw)

def run_xgb(weight, n_seeds, depth=6, add_g5=False, wexp=3):
    trf = engineer(tr_raw, gs, g5s, add_g5); hof = engineer(ho_raw, gs, g5s, add_g5)
    X,y,Xh,yh = split_xy(trf,hof); preds=np.zeros(len(Xh))
    for s in range(n_seeds):
        Xt,Xv,yt,yv = train_test_split(X,y,test_size=0.2,random_state=s)
        wt = (1+wexp*yt) if weight else None
        m=xgb(s,depth); m.fit(Xt,yt,sample_weight=wt,eval_set=[(Xv,yv)],verbose=False)
        preds+=np.clip(m.predict(Xh),0,1)
    return preds/n_seeds, yh

def run_lgbm(n_seeds, add_g5=False, wexp=3):
    trf = engineer(tr_raw, gs, g5s, add_g5); hof = engineer(ho_raw, gs, g5s, add_g5)
    X,y,Xh,yh = split_xy(trf,hof); preds=np.zeros(len(Xh))
    for s in range(n_seeds):
        p=dict(objective='regression',learning_rate=0.03,num_leaves=63,min_child_samples=40,
               feature_fraction=0.8,bagging_fraction=0.8,bagging_freq=1,lambda_l2=1.0,verbose=-1,seed=s)
        m=lgb.train(p,lgb.Dataset(X,y,weight=1+wexp*y),num_boost_round=300,callbacks=[lgb.log_evaluation(0)])
        preds+=np.clip(m.predict(Xh),0,1)
    return preds/n_seeds, yh

base,yh = run_xgb(True,5); print(f'{"XGB w+5seed (best so far)":34s} R2={r2_score(yh,base):.4f}')
for wexp in [5,8]:
    p,_=run_xgb(True,5,wexp=wexp); print(f'{"  weight 1+"+str(wexp)+"*y":34s} R2={r2_score(yh,p):.4f}')
for d in [7,8]:
    p,_=run_xgb(True,5,depth=d); print(f'{"  depth "+str(d):34s} R2={r2_score(yh,p):.4f}')
pg,_=run_xgb(True,5,add_g5=True); print(f'{"  + g5_mean fallback":34s} R2={r2_score(yh,pg):.4f}')
plg,_=run_lgbm(5); print(f'{"LGBM w+5seed (same features)":34s} R2={r2_score(yh,plg):.4f}')
print(f'{"BLEND 0.5*XGB + 0.5*LGBM":34s} R2={r2_score(yh,0.5*base+0.5*plg):.4f}')
print(f'{"BLEND 0.6*XGB + 0.4*LGBM":34s} R2={r2_score(yh,0.6*base+0.4*plg):.4f}')
