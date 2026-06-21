from src import (etl, hotspots, scoring, lq, enrich, forecast, nb_forecast,
                 optimizer, backtest, watchlist, kpis)

if __name__ == "__main__":
    etl.run()
    hotspots.run()
    scoring.run()
    scoring.build_hourly_heat()
    lq.run()
    enrich.run()
    forecast.run_best()
    nb_forecast.run()
    optimizer.run()
    backtest.run()
    watchlist.run()
    kpis.run()
    print("\nPipeline complete. artifacts/ refreshed.")
