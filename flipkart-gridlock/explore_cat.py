"""Round 5: CatBoost (native categoricals incl. geohash) standalone + XGB blend.
Day-49 holdout, leak-safe."""
import numpy as np, pandas as pd, pygeohash as pgh
from xgboost import XGBRegressor
from catboost import CatBoostRegressor, Pool
from sklearn.metrics import r2_score
from sklearn.model_selection import train_test_split

train = pd.read_csv('dataset/train.csv')
d48 = train[train.day==48]; d49 = train[train.day==49].reset_index(drop=True)
rng = np.random.RandomState(0); mask = rng.rand(len(d49))<0.5
tr_raw = pd.concat([d48, d49[mask]], ignore_index=True); ho_raw = d49[~mask].reset_index(drop=True)
gstat = tr_raw.groupby('geohash')['demand'].agg(geohash_mean='mean', geohash_std='std'); gstat['geohash_std']=gstat['geohash_std'].fillna(0)
GM = gstat['geohash_mean'].mean()

def base_eng(df):
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
    df['LargeVehicles']=df['LargeVehicles'].fillna('Unknown'); df['Landmarks']=df['Landmarks'].fillna('Unknown')
    df['g5']=df['geohash'].str[:5]
    return df

tr=base_eng(tr_raw); ho=base_eng(ho_raw)
yh=ho['demand'].values; y=tr['demand'].values

# ---- XGB reference (one-hot) ----
def xgb_eng(df):
    return pd.get_dummies(df.drop(['geohash','g5'],axis=1), columns=['RoadType','LargeVehicles','Landmarks','Weather'], drop_first=True)
Xx=xgb_eng(tr).drop(['demand','Index','timestamp','minute'],axis=1,errors='ignore')
Xxh=xgb_eng(ho).drop(['demand','Index','timestamp','minute'],axis=1,errors='ignore').reindex(columns=Xx.columns,fill_value=0)
def run_xgb(n=5,w=8):
    p=np.zeros(len(Xxh))
    for s in range(n):
        Xt,Xv,yt,yv=train_test_split(Xx,y,test_size=0.2,random_state=s)
        m=XGBRegressor(n_estimators=2000,learning_rate=0.05,max_depth=6,subsample=0.8,colsample_bytree=0.8,
            min_child_weight=3,reg_alpha=0.1,reg_lambda=1.0,early_stopping_rounds=50,tree_method='hist',device='cpu',random_state=s)
        m.fit(Xt,yt,sample_weight=1+w*yt,eval_set=[(Xv,yv)],verbose=False); p+=np.clip(m.predict(Xxh),0,1)
    return p/n
xgbp=run_xgb(); print(f'{"XGB w8 5seed (ref)":38s} R2={r2_score(yh,xgbp):.4f}')

# ---- CatBoost with native categoricals ----
CATS=['RoadType','LargeVehicles','Landmarks','Weather']
NUM=['time_of_day','hour_sin','hour_cos','is_peak','lat','lon','NumberofLanes','Temperature','geohash_mean','geohash_std','lanes_x_highway']
def run_cat(cols_cat, n=5, w=8, depth=8):
    feats=NUM+cols_cat; p=np.zeros(len(ho))
    for s in range(n):
        Xt,Xv,yt,yv=train_test_split(tr[feats],y,test_size=0.2,random_state=s)
        wt=1+w*yt
        m=CatBoostRegressor(iterations=3000,learning_rate=0.05,depth=depth,l2_leaf_reg=3.0,
            loss_function='RMSE',random_seed=s,verbose=False,early_stopping_rounds=50)
        m.fit(Pool(Xt,yt,cat_features=cols_cat,weight=wt),eval_set=Pool(Xv,yv,cat_features=cols_cat),verbose=False)
        p+=np.clip(m.predict(ho[feats]),0,1)
    return p/n
catp=run_cat(CATS); print(f'{"CatBoost cats(road..) w8 5seed":38s} R2={r2_score(yh,catp):.4f}')
catg=run_cat(CATS+['geohash']); print(f'{"CatBoost + geohash cat":38s} R2={r2_score(yh,catg):.4f}')
catg5=run_cat(CATS+['g5']); print(f'{"CatBoost + g5 cat":38s} R2={r2_score(yh,catg5):.4f}')
best_cat = max([(catp,'road'),(catg,'+gh'),(catg5,'+g5')], key=lambda t:r2_score(yh,t[0]))[0]
for wgt in [0.3,0.4,0.5]:
    print(f'{"BLEND "+str(1-wgt)+" XGB + "+str(wgt)+" CAT":38s} R2={r2_score(yh,(1-wgt)*xgbp+wgt*best_cat):.4f}')
