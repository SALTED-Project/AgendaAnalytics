import os
import logging
import pandas as pd
from dynaconf import settings
from simcore_api_schema_mod import Status

from nlpcore.nlpcore_mod import NLPCore
from utils.resultwriter_mod import Resultwriter
from utils.preprocessing_mod import Preprocessing
from handlers.abstract_handler_mod import AbstractHandler

REFFOLDERNAME = settings.REFFOLDERNAME
ANAFOLDERNAME = settings.ANAFOLDERNAME
RESFOLDERNAME = settings.RESFOLDERNAME

logger = logging.getLogger(os.path.basename(__file__))


class DetailedHandler(AbstractHandler):
    """
    Handler class that splits the reference and analysis documents
    into sentences and generates 2D heatmaps for each combination
    of documents with respect to the most relevant sentences
    """

    def __init__(self):
        self.nlpcore = NLPCore()
        self.writer = Resultwriter()
        self.prepro = Preprocessing()
        self.tag = "detailed"
        return

    ###################################################
    #
    # analyze project. project folder is relative to
    # the project ROOT.
    #
    def analyze_project(self, project: str):

        #
        # keep track of generated files
        #
        generated_files = []
        #
        # loop over the files in the reference and analysis folder
        #
        anadir = os.path.join(project, ANAFOLDERNAME)
        refdir = os.path.join(project, REFFOLDERNAME)

        anafiles = os.listdir(anadir)
        reffiles = os.listdir(refdir)

        for anafile in anafiles:
            #
            # for each company text we generate a birds-eye analysis
            #
            absanafile = os.path.join(anadir, anafile)
            anatext = ""
            with open(absanafile, "r") as f:
                anatext = f.read()
                if not anatext:
                    continue

            for reffile in reffiles:

                absreffile = os.path.join(refdir, reffile)
                reftext = ""
                with open(absreffile, "r") as f:
                    reftext = f.read()
                    if not reftext:
                        continue

                print("doing sim for ", absanafile, "against", absreffile)

                #
                # now generate two corpora consisting of the individual
                # document sentences.
                #
                ana_corpus = self.prepro.make_corpus_from_text(anatext)
                ref_corpus = self.prepro.make_corpus_from_text(reftext)
                #
                # in the detailed mode it can happen that some corpora remain
                # empty due to very short sentences. We must not enter further
                # computations then and omit this document. Filling a corpus with
                # a default sentence is not advisable because this could cause a
                # 100% match if, by accident, two such corpora get to be compared
                #
                if (not ana_corpus) or (not ref_corpus):
                    logger.warning(f"Encountered empty ana or ref corpus, check results carefully!")
                    continue
                else:
                    l1 = len(ana_corpus)
                    l2 = len(ref_corpus)
                    msg = f"Chunks in analyze/ref corpus: {l1}/{l2}"
                    logger.info(msg)
                #
                # corpora are non-empty. We proceed.
                #
                ana_embeds = self.nlpcore.embed_corpus(ana_corpus)
                ref_embeds = self.nlpcore.embed_corpus(ref_corpus)
                #
                #
                # compute similarity matrix
                #
                simarr = self.nlpcore.gen_sim_matrix(ana_embeds, ref_embeds)
                #
                # generate a similarity dataframe for this file pair based
                # on sentences
                #
                similarity_df = self.prepro.make_df_from_array(simarr, ana_corpus, ref_corpus)
                g = self.writer.write_result_file(
                    similarity_df,
                    root=os.path.join(project, RESFOLDERNAME),
                    name="$".join([anafile, reffile]),
                    tag=self.tag)
                
                #
                # add generated file to main file list
                #
                generated_files += g

        s = Status.SUCCESS
        m = f"{project} analysis done."
        d = {"generated_files": generated_files}
        return s, m, d
