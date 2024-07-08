import logging
import sys
from robocorp.tasks import task
from RPA.Excel.Files import Files as Excel
from Robots import Otomatika_news
from pathlib import Path
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
    try:
        parameters = bot.get_filters()
    except ValueError as v:
        LOGGER.error("An error occured! Please consider this information: VALUE Error: %s" % (v))
        exit(10)

    # Search for the news using the parameters:
    try:
        articles = bot.get_news_from_reuters(parameters)
    except ValueError as v:
        LOGGER.error("An error occured! Please consider this information: VALUE Error: %s, TRACEBACK: %s" % (v, traceback.format_exc()))
        exit(10)
    except UserWarning as w:
        LOGGER.warning(w)

    # Saving the response in an Excel file: 
    qt_news = bot.save_data_excel(parameters, articles)

    # Ask the question to I.A., if exists:
    if parameters.get('ia_question') is not None:
        bot.ask_ia(articles, parameters['ia_question'])
    LOGGER.info(f"All done! {qt_news} was found and saved.")
