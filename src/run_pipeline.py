from src import etl, hotspots, scoring, forecast, optimizer, backtest, watchlist, kpis

if __name__ == "__main__":
    etl.run()
    hotspots.run()
    scoring.run()
    scoring.build_hourly_heat()
    forecast.run_best()
    optimizer.run()
    backtest.run()
    watchlist.run()
    kpis.run()
    print("\nPipeline complete. artifacts/ refreshed.")
