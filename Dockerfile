FROM python

WORKDIR /app

# nlp_pipeline requirements
# install poppler, tesseract, antiword
RUN apt-get update
RUN apt-get install poppler-utils -y
RUN apt-get install tesseract-ocr -y
RUN apt-get install antiword

# postgres
RUN apt-get install -y postgresql-common
RUN /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh -y
RUN apt-get update
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get purge postgresql-
RUN apt-get install -y postgresql-16
RUN apt-get install -y postgresql-client

# nlp_pipeline libraries
RUN pip install -r https://raw.githubusercontent.com/dhopp1/nlp_pipeline/main/requirements.txt
RUN pip install --ignore-installed six
RUN pip install nlp-pipeline

# local_rag_llm requirements
RUN pip install -r https://raw.githubusercontent.com/dhopp1/local_rag_llm/main/requirements.txt
RUN pip install local-rag-llm

# clone streamlit app
RUN git clone https://github.com/dhopp1/streamlit_rag.git
RUN pip install gnews
# exclude gnews because of requests dependency
RUN curl -s https://raw.githubusercontent.com/dhopp1/streamlit_rag/main/requirements.txt | grep -v gnews | xargs pip install