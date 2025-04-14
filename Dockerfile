FROM ubuntu:22.04

WORKDIR /app

### install python
RUN apt-get update
RUN apt-get install -y curl ffmpeg git python3-pip python3-dev python-is-python3
RUN rm -rf /var/lib/apt/lists/*
#RUN apt-get install vim
RUN apt-get update -y
RUN apt-get install -y ninja-build

### nlp_pipeline requirements
RUN apt-get update
RUN apt-get install poppler-utils -y
RUN apt-get install tesseract-ocr -y
RUN apt-get install antiword

# install required python libraries
RUN pip install --upgrade pip==24.0
RUN curl -s https://raw.githubusercontent.com/dhopp1/nlp_pipeline/main/requirements.txt | grep -v '^#' | grep -v xlrd | xargs pip install
RUN pip install xlrd==2.0.1
RUN pip install --ignore-installed six
RUN pip install nlp-pipeline

# download nltk stopwords and sentiment lexicon
RUN python -c "import nltk; nltk.download('stopwords'); nltk.download('vader_lexicon')"

# local vector search requirements
RUN pip install -r https://raw.githubusercontent.com/dhopp1/local_vector_search/main/requirements.txt

### larga requirements
RUN git clone https://github.com/dhopp1/llarga.git
RUN pip install -r https://raw.githubusercontent.com/dhopp1/llarga/main/requirements.txt
RUN pip install lxml-html-clean
