import streamlit as st
from python_news_scraper.getPrettyUrl import get_pretty_url as prettify
from python_news_scraper import scrapeImage
import requests

NEWS_API_ENDPOINT = 'https://newsapi.org/v2/top-headlines?'

st.session_state.initialQuestion = True

if 'buttonClicked' not in st.session_state:
    st.session_state.buttonClicked = False

if 'articleList' not in st.session_state:
    st.session_state.articleList = None

if 'currentArticle' not in st.session_state:
    st.session_state.currentArticle = None

if 'country' not in st.session_state:
    st.session_state.country = None

def displayNews(id: int, integer: int):
    st.session_state.currentArticle = st.session_state.articleList['articles'][id]
    
    if 'messages' in st.session_state:
        st.session_state.messages.clear()

    if 'scrapedArticle' in st.session_state:
        st.session_state.scrapedArticle = False

    st.session_state.buttonClicked = True


def setCountry(country: str) -> None:
    st.session_state.country = country
    

@st.cache_data(ttl=1200)
def fetch_news(country=None, category=None):
    params = {
        'country': country,
        'apiKey': st.secrets["NEWS_API_KEY"]
    }
    if category:
        params['category'] = category
    response = requests.get(NEWS_API_ENDPOINT, params=params)
    jsonObj = response.json()

    for article in jsonObj['articles']:
        if "news.google.com" in article['url']:
                newUrl = prettify(article['url'])
                article['url'] = newUrl    
    
    return jsonObj


st.set_page_config(page_title='News Aggregator')
st.title('News Aggregator')
st.markdown(
         f"""
         <style>
         .stApp {{
             //background-image: url("https://images.unsplash.com/photo-1585241645927-c7a8e5840c42?ixlib=rb-4.0.3&ixid=MnwxMjA3fDB8MHxleHBsb3JlLWZlZWR8Nnx8fGVufDB8fHx8&w=1000&q=80");
             background-attachment: fixed;
             background-size: cover
         }}
         </style>
         """,
         unsafe_allow_html=True
     )

# Choose the country
countries = ['US', 'TR', 'GB', 'IN', 'CA', 'AU', 'FR', 'DE', 'JP', 'CN', 'RU', 'BR', 'MX', 'IT', 'ES', 'KR', 'IL'] # add more countries as needed
selected_country = st.sidebar.selectbox(label='Select a country', options=countries)

# Choose the category
categories = ['All','Business', 'Entertainment', 'General', 'Health', 'Science', 'Sports', 'Technology']
selected_category = st.sidebar.selectbox('Select a category (optional)', categories)

# Fetch the news
if selected_category == 'All':
    news = fetch_news(selected_country)
else:
    news = fetch_news(selected_country, category=selected_category)

st.session_state.articleList = news

i = 0
for article in news['articles']:
    with st.container(border=True):
        st.write('###', article['title'])
        if article['urlToImage']:
            st.image(article['urlToImage'])
        else:
            st.image("https://placehold.co/700x400")

        with st.expander(label="See more"):
            if article['description']:
                st.write(article['description'])
            else:
                st.write("This article has no accessible description, click 'Read Here' to retrieve it.")
            st.button(label="Read Here", key=i, on_click=displayNews, args=(i, 0))
            st.link_button(label="Go To Website", url=article['url'])
    i += 1

if st.session_state.buttonClicked:
    st.switch_page(page="pages/newspage.py")