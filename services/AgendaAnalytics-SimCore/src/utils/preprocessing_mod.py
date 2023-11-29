import os
import logging
import pandas as pd

#import nltk
#try:
#    nltk.download("punkt", download_dir='./data')
#    nltk.data.path.append('./data')
#except:
#    print("./tokenizers exist")

from nltk import tokenize

logger = logging.getLogger(os.path.basename(__file__))


class Preprocessing:
    """
    Class which provides a range of routines for preprocessing texts
    """

    def __init__(self):
        return

    def make_corpus_from_text(self, text, min_word_count=5):
        """
        do a sentence tokenization and keep only sentences having
        min_word_count words in them. Currently min_word_count is not
        used!
        """

        corpus = list()
        sentences = tokenize.sent_tokenize(text)

        for sentence in sentences:
            sentence = sentence.rstrip("\n")
            #
            # test for minimum length
            # No longer suitable for detailed analysis
            #
            #if len(sentence.split(" ")) < min_word_count:
            #    logger.info(f"Omitted: {sentence}")
            #    continue
            corpus.append(sentence)
        return corpus
    

    def make_df_from_array(self, simarr, ana_corpus, ref_corpus) -> pd.DataFrame:
        """
        Generate a dataframe where the sentences are used as index and column names.
        Pandas does not eliminate duplicate indices which is necessary for this purpose.
        Additionally it was asked by the users that the sentences be not truncated for later
        retrieval in the original document!
        """
        df_index = [x for x in ana_corpus]
        df_columns = [x for x in ref_corpus]
        return pd.DataFrame(data=simarr, index=df_index, columns=df_columns)
