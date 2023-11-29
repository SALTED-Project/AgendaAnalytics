import logging
import os

from sentence_transformers import SentenceTransformer, util

logger = logging.getLogger(os.path.basename(__file__))


class NLPCore:

    def __init__(self):
        """
        Initialize NLPCore class that manages a reference text and a 
        text to be analyzed on a 1:1 basis. Any further sophistication has to
        be carried out by the encompassing module that will address the actual
        use case in a more specific way.
        """
        #
        # the main embedder
        #
        #self.model = SentenceTransformer('T-Systems-onsite/cross-en-de-roberta-sentence-transformer')
        #
        # take a very small model for testing the code
        #
        self.model = SentenceTransformer("sentence-transformers/paraphrase-albert-small-v2")
        return
    

    def embed(self, input):
        return self.model.encode(input, convert_to_tensor=True)

    ################################################################
    #
    #       generate embeddings for the reference corpus
    #
    def embed_corpus(self, corpus):
        """
        embed a corpus stored as sentences in a list
        """
        embeddings = self.embed(corpus)
        assert embeddings.shape[0] == len(corpus)
        return embeddings


    ################################################################
    #
    #       generate similarity matrix
    #
    def gen_sim_matrix(self, emb1, emb2):
        """
        generate sim matrix. emb1 and emb2 hereby have to be
        tensorflow tensors. The cosine similarity between all
        encompassing vectors is hereby calculated. We set negative
        similarity values to zero since they actually indicate
        dissimilarity
        """
        simarr = util.cos_sim(emb1, emb2)
        simarr = simarr.numpy()
        simarr[simarr<0.0] = 0.0
        return simarr
