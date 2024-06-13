import streamlit as st
import time as t
from openai import OpenAI
from scraping.web_scrape import scrape_text_with_selenium
from utils.vectorOperations import sendToStore, queryStore

displayArticle = st.session_state.currentArticle
st.session_state.buttonClicked = False

st.title("Article")
st.write("### " + displayArticle['title'])

client = OpenAI(api_key=st.secrets['OPENAI_API_KEY'])

if displayArticle['urlToImage']:
    st.image(displayArticle['urlToImage'])
else:
    st.image("https://placehold.co/700x400")

st.caption(displayArticle['description'])

if 'initialQuestion' not in st.session_state:
    st.session_state.initialQuestion = True


if 'scrapedArticle' not in st.session_state:
    st.session_state.scrapedArticle = False

# Role initialization
if 'sysMessage' not in st.session_state:
    st.session_state.sysMessage = """Your task is to take in content that is acquired from
    a news website with permission, and to reproduce the original news article as it was in the website originally, omitting any content
    that may have been incorrectly included such as cookie warnings, legal details of the publisher, social media information of the publisher, etc. Ensure that your output matches the length and detail of the original article and that you do not forget to include any of the information given. Always translate any content into English. Directly begin outputting the news article, do not write anything other than the article items, if you want to omit something or do something do it without writing any additional content beyond the article."""

# Initialize model
if 'openaiModel' not in st.session_state:
    st.session_state.openaiModel = 'gpt-3.5-turbo-16k'

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []


def summarizeArticle():
    with st.status(label=f"Searching the url {displayArticle['url']}", expanded=False, state="running") as status:
        t.sleep(1.5)
        status.update(label="Scraping web article")
        scrapedArticle = scrape_text_with_selenium("chrome", "chrome", displayArticle['url'])[1]
        status.update(label="Generating article using AI")
        stream = client.chat.completions.create(
            model=st.session_state["openaiModel"],
            messages=[
                {"role": "system", "content": st.session_state.sysMessage },
                {"role": "user", "content": scrapedArticle}
            ],
            stream=True,
            temperature=0.2
        )
        status.update(label="Generation complete!", state="complete")
    
    with st.chat_message("assistant"):
        summarizedArticle = st.write_stream(stream)

    st.session_state.messages.append({"role": "assistant", "content": summarizedArticle})
    st.session_state.scrapedArticle = True
    sendToStore(summarizedArticle)
    

if not st.session_state.scrapedArticle:
    print("It seems like summarizeArticle() failed")
    # summarizeArticle()
    # Display chat history
    for message in st.session_state.messages[1:]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
else:
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


# Display assistant response in chat message container
if prompt := st.chat_input("Say something"):

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        stream = st.write_stream(queryStore())


    st.session_state.messages.append({"role": "assistant", "content": stream})