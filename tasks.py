import logging
import sys
from robocorp.tasks import task
from robocorp import workitems
from RPA.Excel.Files import Files as Excel
from Robots import Otomatika_news
from pathlib import Path
import os
import requests
import traceback

# Logging Config:
stdout = logging.StreamHandler(sys.stdout)
logging.basicConfig(
    level=logging.DEBUG,
    format="[{%(filename)s:%(lineno)d} %(levelname)s - %(message)s",
    # handlers=[stdout], 
    filename="output/output.log",
)
LOGGER = logging.getLogger(__name__)


@task
def rpa_main_core():
    """
    Main core to the RPA. This function will call the RPA robot, search and save news filtering by search phrase, category and date.
    At first, the bot will only works with Reuter's news.
    """

    bot = Otomatika_news()

    # Getting the filters:
    item = workitems.inputs.current
    input_data = item.payload
    print("Processing input data:", input_data)
    # parameters = bot.get_filters()
    parameters = input_data
    if parameters['phrase'] is None or parameters['start_date'] is None or parameters['end_date'] is None:
        error_msg = "ERROR: You must provide the 'phrase', the 'start_date' and the 'end_date' parameters."
        LOGGER.error()
    if parameters['img_size'] is None:
        parameters['img_size'] = "1080w"

    # Search for the news using the parameters:
    try:
        articles = bot.get_news_from_reuters(parameters)
    except ValueError as v:
        LOGGER.error("An error occured! Please consider this information: VALUE Error: %s, TRACEBACK: %s" % (v, traceback.format_exc()))
    except UserWarning as w:
        LOGGER.warning(w)

    # Saving the response in an Excel file: 
    qt_news = bot.save_data_excel(parameters, articles)
    LOGGER.info(f"All done! {qt_news} was found and saved.")
