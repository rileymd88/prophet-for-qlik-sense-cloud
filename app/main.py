from typing import Union, Literal
from fastapi import Request, FastAPI, HTTPException
import pandas as pd
from datetime import datetime
from prophet import Prophet
from pydantic import BaseModel, RootModel
pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)

class QlikData(BaseModel):
    date: float
    measure: float
    max_date: float | None = None
    frequency: Literal["hour","day", "month"] = "month"
    periods: int = 12
    changepoint: float = 0.05
    yhat: Literal["yhat", "yhat_lower", "yhat_upper"] = "yhat"
    
class ProphetRequest(RootModel):
    root: list[QlikData]
    
def get_freq(frequency: Literal["hour","day", "month"]) -> str:
    if frequency == "hour":
        return "H"
    elif frequency == "day":
        return "D"
    elif frequency == "month":
        return "MS"

def handle_request(data: list[QlikData], script: bool) -> str:
    # Validate mandatory fields    
    if not data or not all(hasattr(item, 'date') and hasattr(item, 'measure') for item in data):
        raise ValueError("Missing mandatory fields: 'date' and 'measure' are required")
    
    # Convert Pydantic models to dictionaries
    df = pd.DataFrame([item.model_dump() for item in data])
    
    # Convert date to datetime
    df['date'] = pd.to_numeric(df['date'], errors='coerce')  # Handle any non-numeric values
    df['date'] = df['date'].dropna().apply(lambda x: datetime.fromordinal(datetime(1900, 1, 1).toordinal() + int(x) - 2))
    df = df.rename(columns={"date": "ds", "measure":"y"})
    
    # Filter data based on max_date
    if data[0].max_date:
        max_date = datetime.fromordinal(datetime(1900, 1, 1).toordinal() + int(float(data[0].max_date)) - 2)
    else:
        # Find the latest date where measure is not 0 or null
        max_date = df[df['y'].notna() & (df['y'] != 0)]['ds'].max()
    
    # Filter data based on max_date
    df_filtered = df[df['ds'] <= max_date]
        
    # Fit the model
    if data[0].frequency == "month":
        print("Monthly forecast")
        m = Prophet(weekly_seasonality=False, changepoint_prior_scale=data[0].changepoint)
        m.add_seasonality(name='monthly', period=30.5, fourier_order=5)
        m.fit(df_filtered)
    else:
        m = Prophet(changepoint_prior_scale=data[0].changepoint)
        m.fit(df_filtered)
    
    # Make the forecast
    freq = get_freq(data[0].frequency)
    future = m.make_future_dataframe(periods=data[0].periods, freq=freq, include_history=False)
    forecast = m.predict(future)
    
    # Return the forecast
    if script:
        return forecast.to_json(orient='records')
    else:
        # Only select the requested forecast column (yhat, yhat_lower, or yhat_upper)
        result_df = forecast[['ds', data[0].yhat]]
        
        # Keep the original dataframe with both date and measure
        original_df = df[['ds', 'y']].copy()
        
        # Merge with forecast results, keeping original order and all columns
        final_df = pd.merge(original_df, result_df, on='ds', how='left')
        
        # Where we have actual values (y), use those instead of forecast
        final_df[data[0].yhat] = final_df.apply(
            lambda row: row['y'] if pd.notna(row['y']) and row['y'] != 0 else row[data[0].yhat],
            axis=1
        )
        
        # Return both the actual/forecasted values and original measures
        # Return only the forecasted values to adhere to Qlik Sense expression requirements
        return final_df[[data[0].yhat]].to_json(orient='records')


app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.post("/prophetScript")
async def prophet_script(request: Request):
    try:
        json_data = await request.json()
        data = ProphetRequest(root=json_data)
        return handle_request(data.root, True)
    except ValueError as e:
        print(e)
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/prophet")
async def prophet(request: Request):
    try:
        json_data = await request.json()
        print(json_data[0])
        data = ProphetRequest(root=json_data)
        return handle_request(data.root, False)
    except ValueError as e:
        print(e)
        raise HTTPException(status_code=400, detail=str(e))