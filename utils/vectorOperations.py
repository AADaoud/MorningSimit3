from openai import OpenAI
from typing_extensions import override
from openai import AssistantEventHandler
import streamlit as st
import time as t

client = OpenAI()
OPENAI_API_KEY = st.secrets['OPENAI_API_KEY']


if 'threadID' not in st.session_state:
    st.session_state.threadID = ''

@st.cache_resource
def createVectorStore():
    if not client.beta.vector_stores.retrieve(vector_store_id=st.secrets['VECTOR_STORE_ID']):
        vector_store = client.beta.vector_stores.create("NewsVectorStore")
    else:
        vector_store = client.beta.vector_stores.retrieve(vector_store_id=st.secrets['VECTOR_STORE_ID'])

    return vector_store

@st.cache_resource
def createAssistant(_vector_store):
    assistant = client.beta.assistants.create(
    name="News Analyst GPT",
    instructions="You are an expert News analyst. Use you knowledge base to answer questions about different news topics.",
    model="gpt-3.5-turbo",
    tools=[{"type": "file_search"}],
    tool_resources={"file_search": {"vector_store_ids": [_vector_store.id]}},
    )

    return assistant

@st.cache_data
def sendToStore(summary):
    vector_store = createVectorStore()

    # Convert to bytes (can be optimized)
    with open(file="./temps/tempfile.md", mode='w', errors='ignore') as file:
        file.write(summary)
    with open(file="./temps/tempfile.md", mode='rb') as file:
        file_batch = client.beta.vector_stores.file_batches.upload_and_poll(vector_store_id=vector_store.id, files=[file])

        while file_batch.status == 'in_progress':
            t.sleep('0.5')
            continue
        
    # TODO more graceful handling of errors uploading to vector store
    if (file_batch.status == 'cancelled' or file_batch.status == 'failed'):
        print("Error uploading files to vector store")
        sendToStore(summary)

    print("Success!")


 
# Create a thread and attach the file to the message
def createThread(messages):
    thread = client.beta.threads.create(
    messages=messages,
    )
    st.session_state.threadID = thread.id
    return thread

def appendToThread(messages):
    if 'threadID' not in st.session_state:
        raise ("No thread ID found!")

    message = messages[-1]

    print(message)

    threadID = st.session_state.threadID

    client.beta.threads.messages.create(
        thread_id=threadID,
        role=message['role'],
        content=message['content']
    )


class EventHandler(AssistantEventHandler):
    @override
    def on_text_created(self, text) -> None:
        print(f"\nassistant > ", end="", flush=True)

    @override
    def on_tool_call_created(self, tool_call):
        print(f"\nassistant > {tool_call.type}\n", flush=True)

    @override
    def on_message_done(self, message) -> None:
        # print a citation to the file searched
        message_content = message.content[0].text
        annotations = message_content.annotations
        citations = []
        for index, annotation in enumerate(annotations):
            message_content.value = message_content.value.replace(
                annotation.text, f"[{index}]"
            )
            if file_citation := getattr(annotation, "file_citation", None):
                cited_file = client.files.retrieve(file_citation.file_id)
                citations.append(f"[{index}] {cited_file.filename}")

        print(message_content.value)
        print("\n".join(citations))


def queryStore():
    messages = st.session_state.messages
    print(messages)
    vector_store = createVectorStore()
    print(f"Created vector store with ID {vector_store.id}")
    assistant = createAssistant(vector_store)

    if st.session_state.initialQuestion:
        thread = createThread(messages)
        st.session_state.threadID = thread.id
    elif not st.session_state.initialQuestion and st.session_state.threadID:
        appendToThread(messages)
        thread = client.beta.threads.retrieve(thread_id=st.session_state.threadID)
    
    st.session_state.initialQuestion = False
    print("entered stream")
    
    with client.beta.threads.runs.stream(
        thread_id=thread.id,
        assistant_id=assistant.id,
        # instructions="Please answer the users query, using your knowledge base for context if suitable.",
        event_handler=EventHandler(),
    ) as stream:
       print("exited stream!")
       for text in stream.text_deltas:
           yield text