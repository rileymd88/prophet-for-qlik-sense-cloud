# Prophet Forecasting for Qlik Sense Cloud

A FastAPI-based service that provides time series forecasting capabilities using Facebook Prophet, designed to integrate with Qlik Sense Cloud.

## Server Setup
Ensure you have Python installed.

Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
```

Install requirements:
```bash
pip install -r requirements.txt
```

Start the server:
```bash
uvicorn app.main:app --reload --port 8000
```

Create an advanced analytics connection in Qlik Sense Cloud pointing to your server:
https://help.qlik.com/en-US/cloud-services/Subsystems/Hub/Content/Sense_Hub/LoadData/ac-advanced-analytic-create.htm

## API Endpoints

### GET /
Health check endpoint that returns a simple "Hello World" message.

### POST /prophet
Processes time series data and returns forecasted values. Meant to be used in front end expressions.

**Request Body Format:**
```json
[{
    "date": float,        // Date in Excel format
    "measure": float,     // Value to forecast
    "frequency": string,  // "hour", "day", or "month" (default: "month")
    "periods": int,       // Number of periods to forecast (default: 12)
    "changepoint": float, // Changepoint prior scale (default: 0.05)
    "yhat": string       // "yhat", "yhat_lower", or "yhat_upper" (default: "yhat")
}]
```

### POST /prophetScript
Processes time series data and returns forecasted values. Meant to be used in the load script.

**Request Body Format:**
```json
[{
    "date": float,        // Date in Excel format
    "measure": float,     // Value to forecast
    "frequency": string,  // "hour", "day", or "month" (default: "month")
    "periods": int,       // Number of periods to forecast (default: 12)
    "changepoint": float, // Changepoint prior scale (default: 0.05)
    "yhat": string       // "yhat", "yhat_lower", or "yhat_upper" (default: "yhat")
}]
```

## Demo app
You can find a demo app called "Prophet.qvf" included in this repository.

## Example Qlik Front End Expression
```qlik
endpoints.ScriptEvalEx('NNNNS', '{"RequestType":"endpoint", "endpoint":{"connectionname":"Demos:Prophet"}}', date, Sum(measure) as measure, $(periodsVar) as periods, $(changepointVar) as changepoint, '$(yhatVar)' as yhat)
```

## Example Qlik Load Script
```qlik
orders:
LOAD
'month' as frequency,
$(periodsVar) as periods,
MakeDate(Year(OrderDate), Month(OrderDate), 1) as date,
Sum(Revenue) as measure
Group by MakeDate(Year(OrderDate), Month(OrderDate), 1)
;
LOAD
    OrderDate,
    Revenue
FROM [lib://DataFiles/__QlikSenseWorkShop - DEMO.xlsx]
(ooxml, embedded labels, table is Orders);

[forecast]:
Load
*
,
timestamp((ds/1000/ 86400) + 25569)  as date
;
LOAD * EXTENSION endpoints.ScriptEval('{"RequestType":"endpoint", "endpoint":{"connectionname":"Demos:Prophet script"}}', orders);
```


