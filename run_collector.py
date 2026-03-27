from tripTimeTracker.collector import update_db
import logging

logging.basicConfig(
    filename='collector.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

if __name__ == "__main__":
    try:
        timestamp = update_db()
        logging.info(f"Saved record at timestamp: {timestamp}")
    except Exception as e:
        logging.exception(f"Error during data collection: {e}")