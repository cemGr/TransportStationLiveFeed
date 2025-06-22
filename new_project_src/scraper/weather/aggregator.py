import pandas as pd
from sklearn.cluster import KMeans  # fallback stub if missing

class WeatherAggregator:

    @staticmethod
    def aggregate(trips: pd.DataFrame, weather: pd.DataFrame) -> pd.DataFrame:
        df = trips.copy()
        df["slot_ts"]    = df["start_time"].dt.floor("h")
        df["hour_of_day"]= df["slot_ts"].dt.hour
        df["weekday_num"]= df["slot_ts"].dt.weekday
        df["is_weekend"] = df["weekday_num"].isin([5, 6])

        # station coords + clustering
        stations = (
            df[["start_station", "start_lat", "start_lon"]]
              .drop_duplicates()
              .rename(columns={
                 "start_station": "station_id",
                 "start_lat": "lat",
                 "start_lon": "lon"
              })
        )
        if not stations.empty:
            kmeans = KMeans(n_clusters=min(80, len(stations)), random_state=0)
            stations["cluster_id"] = kmeans.fit_predict(stations[["lat", "lon"]])
        else:
            stations["cluster_id"] = []

        taken = (
            df.groupby(["slot_ts", "start_station"])
              .size()
              .reset_index(name="bikes_taken")
              .rename(columns={"start_station":"station_id"})
        )
        returned = (
            df.groupby(["slot_ts", "end_station"])
              .size()
              .reset_index(name="bikes_returned")
              .rename(columns={"end_station":"station_id"})
        )

        agg = pd.merge(
            taken, returned, on=["slot_ts","station_id"], how="outer"
        ).fillna({"bikes_taken":0,"bikes_returned":0})
        agg[["bikes_taken","bikes_returned"]] = agg[["bikes_taken","bikes_returned"]].astype(int)

        weather["slot_ts"] = weather["time"].dt.floor("h")
        wh = (
            weather.groupby("slot_ts")
                   .agg(
                     temperature_2m=("temperature_2m","mean"),
                     rain_mm=("rain","mean"),
                     weather_code=("weather_code", lambda x: x.mode().iloc[0] if not x.mode().empty else None)
                   )
                   .reset_index()
        )
        wh["is_raining"] = wh["rain_mm"] >= 0.1
        def temp_class(t: float) -> str:
            if t < 10: return "cold"
            if t < 20: return "mid"
            if t < 28: return "warm"
            return "hot"
        wh["temp_class"] = wh["temperature_2m"].apply(temp_class)

        agg = (
            agg.merge(stations, on="station_id", how="left")
               .merge(wh, on="slot_ts", how="left")
        )

        # season
        season_map = {
          12:"Winter",1:"Winter",2:"Winter",
          3:"Spring",4:"Spring",5:"Spring",
          6:"Summer",7:"Summer",8:"Summer",
          9:"Fall",10:"Fall",11:"Fall"
        }
        agg["season"] = agg["slot_ts"].dt.month.map(season_map)

        return agg
