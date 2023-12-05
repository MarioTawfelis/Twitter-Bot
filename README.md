# Twitter Bot

This is a Python script for a Twitter bot designed to automate liking tweets from specified target users. The bot utilizes the Selenium library to interact with the Twitter web interface and the Airtable API to manage data.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Setup](#setup)
- [Usage](#usage)
- [Configuration](#configuration)
- [Scheduled Execution](#scheduled-execution)
- [Logging](#logging)

## Prerequisites
Before using the Twitter bot, ensure that you have the following installed:
- [Python](https://www.python.org/) (>= 3.6)
- [Mozilla Firefox](https://www.mozilla.org/en-US/firefox/new/)
- [Geckodriver](https://github.com/mozilla/geckodriver/releases) (Ensure it's in your system's PATH)
- [Airtable Account](https://airtable.com/) (for managing data)

## Setup
1. Clone the repository:
   ```bash
   git clone https://github.com/MarioTawfelis/twitter-bot.git
   cd twitter-bot
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables by creating a `.env` file in the root directory:
   ```env
   BASE_ID=your_airtable_base_id
   API_KEY=your_airtable_api_key
   ```

4. Create a `Logs` directory in the root for log files.

5. Create a `Cookies` directory in the root for storing cookie files.

## Usage
Run the script using the following command:
```bash
python main.py
```


## Configuration
Configure the bot by adjusting the following variables in the script:
- `CONFIRMATION_SUBJECT`: Subject of the confirmation email for Twitter.
- `WAIT_TIME`: Maximum wait time for Selenium actions.

## Scheduled Execution
The script includes a scheduling mechanism using the `schedule` library. By default, it runs the main function every 90 minutes. Adjust the scheduling parameters as needed.

```python
# Example: Run main every 90 minutes
schedule.every(90).minutes.do(main)
```

## Logging
Log files are stored in the `Logs` directory. The log file name includes a timestamp for each run.

For any issues or errors, refer to the log files for detailed information.

Feel free to customize the script further based on your specific use case and requirements.
