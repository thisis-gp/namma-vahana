"""Round 3: feature additions + weight/seed tuning on the 91.24 XGB pipeline.
Day-49 holdout, leak-safe (stats from train portion only). Smoothed target encoding."""
import numpy as np, pandas as pd, pygeohash as pgh
from xgboost import XGBRegressor
from sklearn.metrics import r2_score
from sklearn.model_selection import train_test_split

train = pd.read_csv('dataset/train.csv')
d48 = train[train.day==48]; d49 = train[train.day==49].reset_index(drop=True)
rng = np.random.RandomState(0); mask = rng.rand(len(d49))<0.5
tr_raw = pd.concat([d48, d49[mask]], ignore_index=True); ho_raw = d49[~mask].reset_index(drop=True)

GLOBAL = tr_raw['demand'].mean()
def smooth_enc(df, keys, alpha):
    g = df.groupby(keys)['demand'].agg(['sum','count'])
    return ((g['sum'] + alpha*GLOBAL) / (g['count'] + alpha))

# precompute encodings from train portion
enc_gh   = smooth_enc(tr_raw, ['geohash'], 10)
enc_ghh  = smooth_enc(tr_raw.assign(hour=tr_raw.timestamp.str.split(':').str[0].astype(int)), ['geohash','hour'], 20)
enc_ght  = smooth_enc(tr_raw, ['geohash','timestamp'], 5)
enc_g5h  = smooth_enc(tr_raw.assign(g5=tr_raw.geohash.str[:5], hour=tr_raw.timestamp.str.split(':').str[0].astype(int)), ['g5','hour'], 30)

def engineer(df, add=()):
    df = df.copy()
    df[['hour','minute']] = df['timestamp'].str.split(':', expand=True).astype(int)
    df['time_of_day'] = df['hour']*60 + df['minute']
    df['hour_sin'] = np.sin(2*np.pi*df['hour']/24); df['hour_cos'] = np.cos(2*np.pi*df['hour']/24)
    df['is_peak'] = df['hour'].isin([7,8,9,17,18,19]).astype(int)
    df['lat'] = df['geohash'].apply(lambda x: pgh.decode(x)[0]); df['lon'] = df['geohash'].apply(lambda x: pgh.decode(x)[1])
    gstd = tr_raw.groupby('geohash')['demand'].std().fillna(0)
    df['geohash_mean'] = df['geohash'].map(enc_gh).fillna(GLOBAL)
    df['geohash_std']  = df['geohash'].map(gstd).fillna(0)
    if 'ghh' in add:
        df['enc_gh_hour'] = df.set_index(['geohash','hour']).index.map(enc_ghh).astype(float)
        df['enc_gh_hour'] = df['enc_gh_hour'].fillna(df['geohash_mean']).values
    if 'ght' in add:
        df['enc_gh_ts'] = df.set_index(['geohash','timestamp']).index.map(enc_ght).astype(float)
        df['enc_gh_ts'] = pd.Series(df['enc_gh_ts'].values, index=df.index).fillna(df['geohash_mean']).values
    if 'g5h' in add:
        df['g5']=df.geohash.str[:5]
        df['enc_g5_hour'] = df.set_index(['g5','hour']).index.map(enc_g5h).astype(float)
        df['enc_g5_hour'] = pd.Series(df['enc_g5_hour'].values, index=df.index).fillna(df['geohash_mean']).values
        df.drop('g5',axis=1,inplace=True)
    df['lanes_x_highway'] = df['NumberofLanes']*(df['RoadType']=='Highway').astype(int)
    df['Temperature'] = df['Temperature'].fillna(df['Temperature'].median())
    df['Weather'] = df['Weather'].fillna('Sunny'); df['RoadType'] = df['RoadType'].fillna('Residential')
    df = pd.get_dummies(df, columns=['RoadType','LargeVehicles','Landmarks','Weather'], drop_first=True)
    return df

DROP=['demand','Index','geohash','timestamp']
def xgb(seed, depth=6):
    return XGBRegressor(n_estimators=2000, learning_rate=0.05, max_depth=depth, subsample=0.8,
        colsample_bytree=0.8, min_child_weight=3, reg_alpha=0.1, reg_lambda=1.0,
        early_stopping_rounds=50, tree_method='hist', device='cpu', random_state=seed)

def evaluate(label, add=(), wexp=5, n_seeds=5, depth=6):
    trf=engineer(tr_raw,add); hof=engineer(ho_raw,add)
    X=trf.drop([c for c in DROP if c in trf],axis=1); y=trf['demand'].values
    Xh=hof.reindex(columns=X.columns,fill_value=0); yh=hof['demand'].values
    preds=np.zeros(len(Xh))
    for s in range(n_seeds):
        Xt,Xv,yt,yv=train_test_split(X,y,test_size=0.2,random_state=s)
        m=xgb(s,depth); m.fit(Xt,yt,sample_weight=1+wexp*yt,eval_set=[(Xv,yv)],verbose=False)
        preds+=np.clip(m.predict(Xh),0,1)
    print(f'{label:38s} R2={r2_score(yh,preds/n_seeds):.4f}')

evaluate('current (w5, 5seed)')
evaluate('w8, 5seed', wexp=8)
evaluate('w5 + geohash-hour enc', add=('ghh',))
evaluate('w5 + geohash-timestamp enc', add=('ght',))
evaluate('w5 + g5-hour enc', add=('g5h',))
evaluate('w5 + gh-hour + gh-ts', add=('ghh','ght'))
evaluate('w8 + gh-hour + gh-ts, 7seed', add=('ghh','ght'), wexp=8, n_seeds=7)
