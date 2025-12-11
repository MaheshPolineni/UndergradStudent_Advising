import os
import json
import datetime
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import requests
from langchain_community.document_loaders import TextLoader
from langchain_community.document_loaders import CSVLoader
from langchain_community.document_loaders import JSONLoader
from langchain_community.document_loaders import UnstructuredURLLoader
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain_community.chat_models import ChatOllama
from langchain_community.chat_models import ChatOpenAI
from langchain.chains.conversational_retrieval.base import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain.memory import ConversationBufferWindowMemory
from langchain.memory import ConversationSummaryMemory
from langchain_core.prompts import PromptTemplate
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate,MessagesPlaceholder





"""
few_shot_prompt = 

"""
'''This is to get Content from URL and save as a file'''
# def get_page_content(url):
#     response = requests.get(url)
#     soup = BeautifulSoup(response.text, 'html.parser')
#     return soup.get_text()
# urls = [
#     "https://catalog.lamar.edu/college-arts-sciences/computer-science/computer-science-ms/#text"
# ]

# documents = [get_page_content(url) for url in urls]

# with open("C:\\Users\\Mahesh\Documents\\Rag_CS_Documents\\overview.txt", "w", encoding="utf-8") as f:
#     f.write(documents[0])
# docs = [Document(page_content=doc) for doc in documents]


def print_prompt(final_prompt, user_query, context, memory):
    # Format the prompt with the user query, context, and history
    formatted_prompt = final_prompt.format_messages(
        question=user_query, 
        context=context, 
        chat_history=memory.chat_memory.messages  # Correctly access the conversation history
    )
    
    # Print the final prompt for debugging purposes
    print("\n--- FINAL PROMPT SENT TO LLM ---")
    for msg in formatted_prompt:
        # Access the type and content correctly
        print(f"{msg.type.capitalize()} message: {msg.content}")  # Use `type` instead of `role`
    print("\n------------------------------------\n")


def degree_audit():
    degree_docs = []
    course_docs = []

    # Load PDF files
    degree_loader = TextLoader("/home/bmt.lamar.edu/mpolineni/Undergrad_data/course_list.txt")
    course_loader = CSVLoader("/home/bmt.lamar.edu/mpolineni/data/cs.csv")

    degree_pages = degree_loader.load()
    course_pages = course_loader.load()

    # Tag and prepare degree documents
    # for doc in degree_pages:
    #     doc.metadata["source"] = "degree_audit"
    #     doc.page_content = "This is related to degree audit: " + doc.page_content
    #     degree_docs.append(doc)

    # Tag and prepare course documents
    for doc in course_pages:
        doc.metadata["source"] = "Fall Course Registration"
        doc.metadata["category"]="Course Registration"
        doc.metadata["semester"]="Fall 2025"
        doc.page_content = "This is related to courses available to register for fall: " + doc.page_content
        course_docs.append(doc)

    return degree_pages  # return a flat list of Document objects   ***********degree_docs +


def csv_loader(file,url):
    loaded_file=[]
    docs = CSVLoader(file)
    loaded_docs=docs.load()
    for doc in loaded_docs:
        doc.metadata["source"]=url
    return loaded_docs

def text_loader(file,url):
    loaded_file=[]
    docs = TextLoader(file)
    loaded_docs=docs.load()
    for doc in loaded_docs:
        doc.metadata["source"]=url
    return loaded_docs

def enrich_chunks_with_metadata(chunks, llm):
    summarizer_prompt = PromptTemplate.from_template(
        "You are a document organizer.\n"
        "Summarize the following document chunk in 1-2 sentences:\n\n{chunk}"
    )
    tagger_prompt = PromptTemplate.from_template(
        "You are a classifier. Classify the content into one of the categories: "
        "['Degree Requirements', 'Course Info', 'Policies', 'Admissions','Scholarships','Undergrad_Research'].\n\n"
        "Chunk:\n{chunk}"
    )
    question_prompt = PromptTemplate.from_template(
        "You are a helpful assistant. Generate 3 relevant and concise student questions based on the following academic content:\n\n{chunk}"
    )

    enriched_chunks = []

    for chunk in chunks:
        text = chunk.page_content

        # Format the prompt to a string
        summary_prompt_str = summarizer_prompt.format_prompt(chunk=text).to_string()
        tag_prompt_str = tagger_prompt.format_prompt(chunk=text).to_string()
        question_prompt_str = question_prompt.format_prompt(chunk=text).to_string()

        # Invoke the LLM with prompt string (or you can pass list of messages)
        summary = llm.invoke(summary_prompt_str).content.strip()
        tag = llm.invoke(tag_prompt_str).content.strip()
        questions_raw = llm.invoke(question_prompt_str).content.strip()

        clean_questions = [q.lstrip("- ").strip() for q in questions_raw.split("\n") if q.strip()]

        chunk.metadata["summary"] = summary
        chunk.metadata["tag"] = tag
        chunk.metadata["sample_questions"] = "\n".join(clean_questions)

        enriched_chunks.append(chunk)
    return enriched_chunks


def add_documents_to_the_db(splitter,chunks,vector_store,metadata_llm):
    splitter.split_documents(chunks)
    enriched_chunks=enrich_chunks_with_metadata(chunks,metadata_llm)
    vector_store.add_documents(enriched_chunks)
    vector_store.persist()
    return 


def webBaseLoader():
    urls=["https://catalog.lamar.edu/college-arts-sciences/computer-science/computer-science-ms/#text",
          "https://www.lamar.edu/financial-aid/withdrawing-and-the-60-dates.html",
        # "https://www.lamar.edu/arts-sciences/computer-science/degrees/graduate/degree-requirements.html",
         "https://catalog.lamar.edu/college-arts-sciences/computer-science/computer-science-ms/#requiredcoursestext",
         ]
    loader=UnstructuredURLLoader(urls)
    docs= loader.load()
    return docs

'''The function adds metadata and merge all documents into a list'''
def document_parsing(folder_path):
    documents=[]

    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if os.path.isfile(file_path):
            loader=TextLoader(file_path,encoding='utf-8')
            docs=loader.load()
            for doc in docs:
                doc.metadata["source"]=filename
                doc.page_content=f"This is a {filename}" + doc.page_content
            documents.extend(docs)
    return documents


clarify_prompt = PromptTemplate(
    input_variables=["question"],
    template=(
        "You are an academic advisor assistant helping students clarify their questions. "
        "Given the student's original question: \"{question}\", rewrite it to be clear, specific, and academically complete. "
        "Ensure it includes the necessary context, subject, and intent so it can be easily understood and answered."
    )
)

system_msg = SystemMessagePromptTemplate.from_template(f"you are an Computer Science department advisor for Undergrad students.You are been querying on {datetime.datetime.now()}."
"Make sure to display only one source which is most relative to the response from the chunks and also make sure do not display any source for which does not have or for general questions like Hello e.t.c"
" If you don't have any information or data politely say refer to youe academic/department advisor, as i don't have the information/If it related to admissions , say to contact admissions office along with the response"
"always do conversation in English"
"If the query is related to CS Faculty/Staff or faculty just say the user to follow the following link - 'https://www.lamar.edu/arts-sciences/computer-science/faculty-staff/'."
"If the query is about admissions act as a Admission department faculty"
"For every response say the student to confirm with the departmrnt")


human_msg = HumanMessagePromptTemplate.from_template(
    "Student Question: {question}\n\n"
    "Use only the following context to answer: {context}\n\n"
    "Chat History: {chat_history}\n\n"
)


final_prompt = ChatPromptTemplate.from_messages([system_msg, human_msg])


filter_prompt = PromptTemplate(
    input_variables=["initial_response","rules"],
    template="you are a very strict officer, who makes sure that the following rules {rules}, are followed by the {initial_response}" \
    "and modify the response accordingly and give the final resposne."
)
# --------------------------------------------------------------------------------------------------------------------------------




load_dotenv()
# degree_requirements_docs=csv_loader("/home/bmt.lamar.edu/mpolineni/data/degree_requirements.csv")
# fall_calender = csv_loader("/home/bmt.lamar.edu/mpolineni/data/fall_calender.csv","https://www.lamar.edu/events/academic-calendar-listing.html")
# summer_calender = csv_loader("/home/bmt.lamar.edu/mpolineni/data/summer_calender.csv","https://www.lamar.edu/events/academic-calendar-listing.html")
# prohibition = text_loader("/home/bmt.lamar.edu/mpolineni/data/Prohibition.txt","https://www.lamar.edu/students/_files/documents/student-success/lu-academic-policies.pdf")
# reg_drop_late = text_loader("/home/bmt.lamar.edu/mpolineni/data/Reg-drop-late.txt","https://www.lamar.edu/students/registrar/registration/")
# undergrad_policies = text_loader("/home/bmt.lamar.edu/mpolineni/data/undergrad-policies.txt","https://catalog.lamar.edu/undergraduate-academic-policies-procedures/")
# undergrad_research=text_loader("/home/bmt.lamar.edu/mpolineni/data/undergrad_research.txt","https://www.lamar.edu/research/index.html")
# admission_process=text_loader("/home/bmt.lamar.edu/mpolineni/data/admission_process.txt","https://www.lamar.edu/admissions/how-to-apply/index.html")
# # degrees_mode=text_loader("/home/bmt.lamar.edu/mpolineni/data/degrees_mode.txt","https://www.lamar.edu/academics/index.php")
# scholarships=text_loader("/home/bmt.lamar.edu/mpolineni/data/scholarships.txt","https://www.lamar.edu/financial-aid/scholarships/index.html")
# cs_degrees=text_loader("/home/bmt.lamar.edu/mpolineni/data/cs_degrees.txt","https://www.lamar.edu/arts-sciences/computer-science/degrees/undergraduate/index.html")
# contact_info=text_loader("/home/bmt.lamar.edu/mpolineni/data/contact_info.txt","https://www.lamar.edu/arts-sciences/computer-science/contact-us.html")
# general=text_loader("/home/bmt.lamar.edu/mpolineni/data/general.txt","https://catalog.lamar.edu/college-arts-sciences/computer-science/computer-science-bs/")
# facilities_resources=text_loader("/home/bmt.lamar.edu/mpolineni/data/facilities_resources.txt","https://www.lamar.edu/arts-sciences/computer-science/facilities/in")
# finincial_aid=text_loader("/home/bmt.lamar.edu/mpolineni/data/finincial_aid.txt","https://www.lamar.edu/financial-aid/financial-aid-handbooks/section-2/index.html")
# student_employment=text_loader("/home/bmt.lamar.edu/mpolineni/data/student_employment.txt","https://www.lamar.edu/arts-sciences/computer-science/employment/index.html")
# CIS=text_loader("/home/bmt.lamar.edu/mpolineni/data/cis.txt","https://www.lamar.edu/arts-sciences/computer-science/degrees/undergraduate/bs-cis.html")
# cybersecurity=text_loader("/home/bmt.lamar.edu/mpolineni/data/cybersecurity.txt","https://www.lamar.edu/arts-sciences/computer-science/degrees/undergraduate/bs-cybersecurity/index.html")
# game_development=text_loader("/home/bmt.lamar.edu/mpolineni/data/game_dev.txt","https://www.lamar.edu/arts-sciences/computer-science/degrees/undergraduate/bs-cybersecurity/index.html")

docs=""
# docs.extend(summer_calender)
# docs.extend(prohibition)
# docs.extend(reg_drop_late)
# docs.extend(undergrad_policies)

splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=40)
chunks = splitter.split_documents(docs)


metadata_llm=ChatOllama(model="mistral-small:latest",temperature=0.4)
# metadata_llm=ChatOpenAI(model_name="gpt-4",temperature=0.4)
# rules=TextLoader("/home/bmt.lamar.edu/mpolineni/Undergrad_data/required_count.txt")
# loader = rules.load()
# rules_chunks=splitter.split_documents(loader)
# chunks_with_metadata= enrich_chunks_with_metadata(chunks,metadata_llm)    
    


embeddings = OllamaEmbeddings(model="mxbai-embed-large")
# embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
persist_directory="./updated_bs_data"
if os.path.exists(persist_directory) and os.listdir(persist_directory):
    #  Load existing vector DB
    vector_store = Chroma(persist_directory=persist_directory, embedding_function=embeddings)
else:
    #  Create it for the first time
    vector_store = Chroma.from_documents(documents=chunks, embedding=embeddings, persist_directory=persist_directory) #Remember chunks - updated Chunks
    vector_store.persist()
 
# add_documents_to_the_db(splitter,game_development,vector_store,metadata_llm)
# vector_store.delete(where={"source": "https://www.lamar.edu/financial-aid/financial-aid-handbooks/section-2/index.html"})

# vector_store.add_documents(chunks_with_metadata)
retriever = vector_store.as_retriever(search_type="similarity",search_kwargs={"k":5}) #,"score_threshold": 0.75

llm=ChatOllama(model="mistral-small:latest",temperature=0.4)
# llm = ChatOpenAI(model_name="gpt-4",temperature=0.1)

# clarify_chain = clarify_prompt | llm

# filter_chain= filter_prompt | llm



# memory = ConversationSummaryMemory(  
#     llm=llm,
#     memory_key="chat_history",
#     return_messages=True,
#     output_key="answer"
# )


def user_chain():

    memory = ConversationBufferWindowMemory(
    memory_key="chat_history",  # Key used in the chain
    k=1,                        # Keep the last 2 messages
    return_messages=True,        
    output_key='answer'
)

    qa_chain = ConversationalRetrievalChain.from_llm(
        llm=llm,    
        retriever=retriever,
        memory=memory,
        # condense_question_llm=clarify_chain,  # Uses your custom clarification prompt
        combine_docs_chain_kwargs={"prompt": final_prompt},
        return_source_documents=True  # optional: shows which doc answers came from
    )
    return qa_chain

# semseter = input("Can i know the term (Fall/Spring) you are quering for:  ")

# result=qa_chain.invoke(f"completed course list: {completed_courses}, \n incomplete courses list: {incomplete_courses_list}\n Semseter: {semseter}")

# print(f"{result['answer']}\n")

# while True:
#     print("input: ")
#     query = input("You: ")
#     if query.lower() in ["exit", "quit"]:
#         # print("👋 Goodbye!")
#         break
#     result = qa_chain.invoke({"question": query})
#     # print(memory.load_memory_variables({})["chat_history"],final_prompt)
#     # print("------------------------------------------------------\n")
#     print(f"\nBot: {result['answer']}\n")


def chat_bot(chain,messgae):
    query = messgae
    if query.lower() in ["exit", "quit"]:
        # print("👋 Goodbye!")
        return
    result = chain.invoke({"question": query})
    source_docs = result.get("source_documents", [])
    urls=set()
    for doc in source_docs:
        urls.add(doc.metadata.get("source"))
    # print(memory.load_memory_variables({})["chat_history"],final_prompt)
    # print("------------------------------------------------------\n")
    return f"\n{result['answer']}\n{', '.join(urls)}"




# retrieved_docs = retriever.get_relevant_documents(" i am not done with any of the courses,this is my 1st semester, can i register for artificial intelligence course")
# # Print the retrieved chunks
# for i, doc in enumerate(retrieved_docs):
#     print(f"\n--- Retrieved Chunk {i+1} ---")
#     print(doc.metadata)
#     print("-------------------metedata----------------------")
#     print(doc.page_content)
#     print("-----------------------------------------------------------------------------------------------------------------")
