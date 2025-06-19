import google.generativeai as genai
from langchain_chroma import Chroma
from langchain.schema import Document
from langchain_community.document_loaders import UnstructuredFileLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import os

API_KEY = os.getenv("API_KEY")
genai.configure(api_key=API_KEY)

# Test docs
doc1 = {"db_id": "0",
        "answer": "We offer a 30-day money-back guarantee on all our products. If you're not satisfied with your "
                  "purchase for any reason, you can request a full refund within 30 days of the purchase date. To "
                  "initiate a refund, please contact our support team with your order details. Refunds are typically "
                  "processed within 5–7 business days."}
doc2 = {"db_id": "1",
        "answer": "Our headquarters are located in Sydney, Australia. While we operate primarily online, our main "
                  "office handles customer support, logistics, and management. If you need to get in touch or visit "
                  "us, please contact our support team to schedule an appointment."}
doc3 = {"db_id": "2",
        "answer": "Once your order has been shipped, you’ll receive a confirmation email with a tracking link and "
                  "number. Simply click the link or enter the tracking number on our shipping partner’s website to "
                  "view real-time updates on your delivery. If you haven’t received a tracking email within 2 "
                  "business days of placing your order, please contact our support team."}

infos = [doc1, doc2, doc3]
docs = [Document(info["answer"], metadata={"ID": info["db_id"]}) for info in infos]


class EmbedClass:
    @staticmethod
    def embed_documents(content):
        response = genai.embed_content(model="gemini-embedding-exp-03-07",
                                       content=content,
                                       task_type="retrieval_document")
        return response["embedding"]

    @staticmethod
    def embed_query(query):
        response = genai.embed_content(model="gemini-embedding-exp-03-07",
                                       content=query,
                                       task_type="retrieval_query")
        return response["embedding"]


# ChromaDB Database
# noinspection PyTypeChecker
vectorstore = Chroma(
    collection_name="faq_answers",
    embedding_function=EmbedClass,
    persist_directory="./chroma_store"
)

if len(vectorstore.get()['ids']) == 0:
    vectorstore.add_documents(docs)

def get_similar(query):
    return vectorstore.similarity_search(query, k=1)[0]


def add_documents(documents):
    vectorstore.add_documents([Document(document) for document in documents])


def process_file(filepath):
    loader = UnstructuredFileLoader(filepath)
    documents = loader.load()

    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_documents(documents)

    print(chunks)

    vectorstore.add_documents(chunks)


# Test
if __name__ == "__main__":
    question = input("Question: ")
    results = vectorstore.similarity_search_with_score(question, k=1)
    doc, score = results[0]
    print(doc, score)
