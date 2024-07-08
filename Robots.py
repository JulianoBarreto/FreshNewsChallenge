import logging
import requests
import warnings
import json
import re
import os
import sys
from robocorp import workitems
from RPA.Excel.Files import Files
from openai import OpenAI

# Logging Config:
stdout = logging.StreamHandler(sys.stdout)
logging.basicConfig(
    level=logging.DEBUG,
    format="[{%(filename)s:%(lineno)d} %(levelname)s - %(message)s",
    # handlers=[stdout], 
    filename="output/output.log",
)
LOGGER = logging.getLogger(__name__)


class Otomatika_news():
        
    def __init__(self, debug=False):
        self.debug = debug 
        # OpenAI Configurations:
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    def get_filters(self):
        """ 
            Get the parameters from environment to search and filter the news. 

            Parameters: 
            None

            Returns:
            dict: Dictionary with all the parameters selected by user (search phrase, start date, end date and image size).
        """
        item = workitems.inputs.current
        parameters = item.payload
        if parameters['phrase'] is None or parameters['start_date'] is None or parameters['end_date'] is None:
            error_msg = "ERROR: You must provide the 'phrase', the 'start_date' and the 'end_date' parameters."
            print(error_msg)
            raise ValueError(error_msg)
        if parameters['img_size'] is None:
            parameters['img_size'] = "1080w"  # Set a default image width (1080px).

        LOGGER.info(f"Processing input data: {json.dumps(parameters)}")
        return parameters

    def get_news_from_reuters(self, par):
        """
            Get the news from Reuters using the paramenters.

            Parameter:
            par(dict): The parameters passed by user (phrase to search, start date, end date, image size to recover).

            Returns:
            dict: Articles found with id, url, title, headline, description, publish date, update date, image url, 
                    thumbnail url, image description, number of times the phrase appears, if money appears.
        """
        main_url = "https://www.reuters.com"
        offset_size = 100  # Number of news to retrieve per page.
        offset = 0  # The offset - actual news.
        url = 'https://www.reuters.com/pf/api/v3/content/fetch/articles-by-search-v2?query=\
                {"end_date":"' + par['end_date'] + '", \
                "keyword":"' + par['phrase'] + '", "offset":"' + str(offset) + '", \
                "orderby":"display_date:desc", "size":"' + str(offset_size) + '", \
                "start_date":"' + par['start_date'] + '", \
                "website":"reuters"}&d=201&_website=reuters'

        LOGGER.info("Getting the news from %s until %s. Searching for '%s'..." % (par['start_date'], par['end_date'], par['phrase']))

        r = requests.get(url)
        response = json.loads(r.text)
        # If the message doesn't return "Success", there's nothing we can do except raise an error:
        message = response['message']
        if message != "Success":  
            raise ValueError(message)
        # If theresn't news, raise a warning:
        total_news = response['result']['pagination']['total_size']
        if total_news <= 0:
            warnings.warn("The search returned 0 results", UserWarning)

        articles= []

        while True:
            # Organizing the articles: 
            for article in response['result']['articles']:
                articles.append({
                    'art_id': article['id'],
                    'art_url': main_url + article['canonical_url'],
                    'title': article['title'],
                    'headline': article['basic_headline'],
                    'desc': article['description'],
                    'pub_date': article['published_time'],
                    'upd_date': article['updated_time'],
                    'img_url': article['thumbnail']['renditions']['original'][par['img_size']],  # 60w 120w 240w 480w 960w 1080w 1200w 1920w
                    'thumb_url': article['thumbnail']['renditions']['square']['120w'],  # 60w 120w 240w 480w 960w 1080w 1200w 1920w
                    'img_desc': article['thumbnail']['caption'] if 'caption' in article['thumbnail'] else "No Caption",  # Description of the image.
                    'count_phrase': self.count_searched_phrase(par['phrase'], article['title']) + 
                    self.count_searched_phrase(par['phrase'], article['description']),  
                    'contains_money': self.contains_money(article['title']) or 
                    self.contains_money(article['description']),  # Test if title or desc contains money.
                })
                offset += 1
            if offset >= total_news:  # If all news was collected, end the loop.
                break
            if offset >= offset_size:  # if have more than 'offset_size' news. Works like pagination.
                url = 'https://www.reuters.com/pf/api/v3/content/fetch/articles-by-search-v2?query=\
                {"end_date":"' + par['end_date'].strftime('%Y-%m-%d') + '", \
                "keyword":"' + par['phrase'] + '", "offset":"' + str(offset) + '", \
                "orderby":"display_date:desc", "size":"' + str(offset_size) + '", \
                "start_date":"' + par['start_date'].strftime('%Y-%m-%d') + '", \
                "website":"reuters"}&d=201&_website=reuters'

                r = requests.get(url)
                response = json.loads(r.text)

        LOGGER.info("Success!")
        return articles

    def save_data_excel(self, par, articles):
        """
        Saves all the retrieved data in an Excel .xlsx file.

        Parameters:
        par (dict): Search parameters used to retrieve the articles.
        articles (list): List of articles retrieved from the search.

        Returns:
        int: Number of news articles saved.
        """
        qt_news_saved = 0
        excel = Files()
        filename = f"output/FreshNews[{par['phrase']}] {par['start_date']}-{par['end_date']}.xlsx"
        excel.create_workbook(filename)
        # excel.create_worksheet("FreshNews")

        LOGGER.info(f"Creating the file with name '{filename}'.")

        col_titles = articles[0].keys()  # Get the titles of the columns
        # rows = [list(col_titles)]  # Starting the rows (with the titles)
        rows = [list(["ID", "News URL", "Title", "Headline", "Description", "Publish Date", "Last Update Date", "Image URL", 
                    "Thumb URL", "Image Description", "Count Phrase", "Contains Money"])]  # Starting the rows (with the titles)

        for article in articles:
            rows.append(list(article.values()))
            qt_news_saved += 1

        excel.append_rows_to_worksheet(rows)  # , header=True, start=2)
        excel.auto_size_columns("A", "L")
        excel.save_workbook()
        excel.close_workbook()
        LOGGER.info("File saved!")

        return qt_news_saved 

    @staticmethod
    def contains_money(str):
        """ Test if a string 'str' contains any kind of money using Regex (Possible formats: $11.1 | $111,111.11 | 11 dollars | 11 USD). 

            Parameter: 
            str (string): String to find money reference. 

            Returns: 
            boolean: Found (True) or not (False).
        """
        money_pattern = re.compile(r'\$\d+(?:,\d{3})*(?:\.\d{2})?|\d+ dollars|\d+ USD')

        if money_pattern.search(str):
            return True
        return False

    @staticmethod
    def count_searched_phrase(phrase, str):
        """ 
            Counts how often the 'phrase' appears in the string 'str'. 

            Parameters:
            phrase(string): The needle to search for.
            str(string): The string to serch for the needle.

            Returns:
            int: Number of times the needle was found.
        """
        return str.lower().count(phrase.lower())

    def ask_ia(self, articles, question):
        """
            Ask 'question' to IA, based on the found news.

            Parameters:
            articles(dict): The news articles found.
            question(string): The question itself.

            Returns:
            Dict: Returns a payload ('ia_response') to Robocorp work item.
        """
        LOGGER.info("Starting the A.I. Bot...")

        # OpenAI Configurations:
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))  # TODO: Need to put this API KEY in the vault.
        model = "gpt-4o"
        prompt = ("You are a news specialist. Your job is to open all the Reuters news links below and use all the information "
                    "gathered to answer the user's question. You MUST OPEN all the Reuters links provided:"
                    "Reuters News Links:"
                    "%news_links%")

        # Feeding with the news links:
        for article in articles:
            links = links + article['art_url'] + "\n"
        # Updating the prompt:
        conversation = [{"role": "system", "content": prompt.replace("%news_links%", links)},]
        conversation.append({"role": "user", "content": question})
        LOGGER.info(f"Question asked: {question}")
        # Startign the chat:
        chat = client.chat.completions.create(
            model=model, messages=conversation
        )
        reply = chat.choices[0].message.content
        # conversation.append({"role": "assistant", "content": reply})
        LOGGER.info(f"The A.I. responded: {reply}")
        processed_data = {"ia_response": reply}
        workitems.outputs.create(payload=processed_data)

