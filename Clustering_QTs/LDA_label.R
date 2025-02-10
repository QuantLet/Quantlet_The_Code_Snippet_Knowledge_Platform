# https://cran.r-project.org/web/packages/seededlda/seededlda.pdf
# https://quanteda.io/reference/tokens.html
#devtools::install_github("quanteda/quanteda.corpora")
library(quanteda)
require(quanteda.corpora)
library(seededlda)
library(lubridate)
library(readtext)

# We map each quantlet to the Quantinar Target Topics

# Target Topics:
# Data Science
# Fintech
# Blockchain
# Explainable AI
# Machine Learning
# Cryptocurrency

### Config
wd = paste0(Sys.getenv('HOME'), '/Desktop/Quantlet_scraping/')
setwd(wd)

# Choose whether to make the topic assignment dependent on the specified keywords or the relevant_text variable. 
# Default version works with KEYWORDS
text_field_var = 'keywords' 
#text_field_var = 'relevant_text' 

# Static
qlet_data = 'Quantlet_Database.json' # Quantlet json
out_file = 'qlet_topics_assigned_v2.csv' # Output file name


# Define dictionary
dict_topic = dictionary(list(datascience=c("data mining", "analytics", "cluster", "Monte Carlo", "SQL", "predict*", "communication", "data clean*", "data science", "data management", "NLP", "natural language processing", "data visualization", "business intelligence", "BI", "random number", "stationary", "regression", "correlation", "dependence", "multivariate*", "visualization"), 
                             fintech=c("api", "regulatory", "regulatory technology", "regtech", "KYC", "AML", "fintech", "fin tech", "3D secure", "Chargeback", "Crowdfunding", "financial", "*financ*"),
                             blockchain=c("blockchain", "block chain", "block*", "coin", "consensus", "POW", "POS", "Proof of Work", "Proof of Stake", "Contract", "Smart Contract", "Cryptography", "Decentralization", "Fork", "Node", "Hash", "Mining", "Byzantine"),
                             explainableai=c('Explainable AI', "Explain*","XAI", "Transparency", "Audit*", "Transparent", "Concept*", "Concept Explanation", "Interpretability", "Econometric*"),
                             machinelearning=c("Machine Learning", "ML", "AI", "XGBoost", "XG", "Tune", "Neural Network", "ARIMA", "NN", "Neural Network", "Deep Learning", "predict*", "forecast*", "LSTM","Supervise", "Classification", "Classifier", "Learner", "Robot", "Overfit*", "SVM", "Support Vector Machine", "Stationarity", "*starionar*", "Gradient Boost", "Boost", "Logistic Regression", "regression", "LDA", "Latent", "Topic Model*", "GAN", "Nadaraya Watson", "FRM"),
                             cryptocurrency=c("crypto*", "Bitcoin", "BTC", "Ether*", "ETH", "Crypto Exchange", "CRIX", "DAI", "Deribit", "Digital Currency", "Digicash", "Digital Wallet", "Wallet", "FIAT", "NFT", "Non-fundigble Token", "Stable Coin", "Stablecoin", "Smart Contract*","Tether", "USDT")
))
print(dict_topic)


qj_unique = jsonlite::fromJSON(qlet_data)

# quantlet names are not unique! this is why we work with the defined 'docid' below
qj_unique['docid'] = paste(qj_unique$repo_name, '-', qj_unique$name_of_quantlet, '-', rownames(qj_unique))

# Construct Corpus from Quantlet JSON
qj_unique$relevant_text = paste(qj_unique$description, qj_unique$keywords)
q_corpus = corpus(qj_unique, text_field = text_field_var, docid_field = 'docid') #switch back to relevant_text!!
summary(q_corpus, n = 5)
ndoc(q_corpus)

toks_news_raw <- tokens(q_corpus, remove_punct = TRUE, remove_numbers = TRUE, remove_symbol = TRUE)
toks_news <- tokens_remove(toks_news_raw, pattern = c(stopwords("en"), "*-time", "updated-*", "gmt", "bst"))

##
dfmat_news <- dfm(toks_news) %>% 
  dfm_trim(min_termfreq = 0.8, termfreq_type = "quantile",
           max_docfreq = 0.1, docfreq_type = "prop")

# Execute seeded LDA
tmod_slda <- textmodel_seededlda(dfmat_news, dictionary = dict_topic)
terms(tmod_slda, 20)
head(topics(tmod_slda), 20)

# assign topics from seeded LDA as a document-level variable to the dfm
dfmat_news$topic2 <- topics(tmod_slda)

# cross-table of the topic frequency
table(dfmat_news$topic2)

# Tests
un_keywords = unique(qj_unique$keywords)

# Inspect outcome for individual topics
tops = topics(tmod_slda)
tops[tops %in% c('cryptocurrency')]

# Save Output
qj_unique$assigned_topic = tops
write.csv(qj_unique, file = out_file)


