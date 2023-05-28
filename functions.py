import xgboost as xgb
import xarray as xr
import numpy as np

ds = xr.open_dataset('weather_forecasts/latest_weather_fc.nc')

def interp_inputs(lat, lon):
    desired_latitude = lat
    desired_longitude = lon

    # interpolate prediction variables
    interp_u = ds['u10'].interp(latitude=desired_latitude, longitude=desired_longitude)
    interp_v = ds['v10'].interp(latitude=desired_latitude, longitude=desired_longitude)
    ds['interp_msl'] = ds['msl'].interp(latitude=desired_latitude, longitude=desired_longitude)
    ds['interp_sp'] = ds['sp'].interp(latitude=desired_latitude, longitude=desired_longitude)
    ds['interp_t2m'] = ds['t2m'].interp(latitude=desired_latitude, longitude=desired_longitude)

    # Calculate Wind Speed and Direction
    wind_speed = np.sqrt(interp_u**2 + interp_v**2)

    wind_direction = np.arctan2(interp_v, interp_u) * (180 / np.pi)
    # Adjust wind direction to range from 0 to 360 degrees
    wind_direction = (wind_direction + 360) % 360

    ds['wind_speed'] = wind_speed
    ds['wind_direction'] = wind_direction

    FEATURES = ['interp_sp', 'interp_msl', 'wind_speed', 'wind_direction', 'interp_t2m']

    # Create a Pandas dataframe from the xarray dataset
    df = ds[FEATURES].to_dataframe()
    df = df.reset_index()
    df = df.set_index('valid_time')
    df = df.drop(columns=['time', 'step', 'meanSea', 'surface', 'heightAboveGround'])
    df = df.rename_axis(index={'valid_time': 'time',})
    df = df.rename(columns={'interp_sp':'sp', 
                            'interp_msl':'msl',
                            'interp_t2m':'t2m',
                        })
    
    return df

def get_windfc(df):
    # Load XGBoost Model
    model = xgb.XGBRegressor()
    model.load_model('models/windModelV3.json')

    # Make predictions
    df['windpower_fc'] = model.predict(df)

    # Predictions between 0 and 1 only
    df['windpower_fc'] = df['windpower_fc'].apply(lambda x: 1 if x > 1 else x)
    df['windpower_fc'] = df['windpower_fc'].apply(lambda x: 0 if x < 0 else x)

    most_recent_forecast = df.drop(columns=['sp', 'msl', 'wind_speed', 'wind_direction', 't2m'])

    return most_recent_forecast.to_json()

def is_outside_uk(latitude, longitude):
    # Define the boundaries of the UK
    uk_latitude_min = 50.0
    uk_latitude_max = 60.0
    uk_longitude_min = -10.0
    uk_longitude_max = 2.0

    # Check if the given latitude and longitude are outside the UK boundary
    if latitude < uk_latitude_min or latitude > uk_latitude_max or longitude < uk_longitude_min or longitude > uk_longitude_max:
        return True
    else:
        return False
