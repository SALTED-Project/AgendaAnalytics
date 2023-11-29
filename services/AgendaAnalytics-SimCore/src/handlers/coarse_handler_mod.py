import os
import logging
import pandas as pd
from dynaconf import settings
from simcore_api_schema_mod import Status

from nlpcore.nlpcore_mod import NLPCore
from utils.resultwriter_mod import Resultwriter
from handlers.abstract_handler_mod import AbstractHandler

REFFOLDERNAME = settings.REFFOLDERNAME
ANAFOLDERNAME = settings.ANAFOLDERNAME
RESFOLDERNAME = settings.RESFOLDERNAME

logger = logging.getLogger(os.path.basename(__file__))


class CoarseHandler(AbstractHandler):
    """
    Handler class that provides a birds-eye similarity analysis
    in the way that all reference documents are compared to all
    company documents but at a document level. Since transformers
    restrict number of tokens to (mainly) 512 we can not expect
    very good results for longer comparisons
    """

    def __init__(self):
        self.nlpcore = NLPCore()
        self.writer = Resultwriter()
        self.tag = "coarse"
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

            resultlist = list()
            for reffile in reffiles:

                absreffile = os.path.join(refdir, reffile)
                reftext = ""
                with open(absreffile, "r") as f:
                    reftext = f.read()
                    if not reftext:
                        continue

                print("doing sim for ", absanafile, "against", absreffile)

                #
                # the "corpus" here consists of only two texts, namely
                # one reference and one analysis text.
                # The result for all references and one analysis text
                # is collected and written out
                #
                mini_corpus = [anatext, reftext]
                #
                # embed the 'corpus' and compute similarity
                #
                embeddings = self.nlpcore.embed_corpus(mini_corpus)
                assert embeddings.shape[0] == 2  # we only have two 'sentences'
                smat = self.nlpcore.gen_sim_matrix(embeddings[0], embeddings[1])
                assert smat.shape == (1, 1)

                #
                # add the current analysis text results to the corresponding
                # result list. It was asked by the users that the texts not be
                # truncated!
                #
                data_tuple = (anafile, anatext, smat.item(), reffile, reftext)
                resultlist.append(data_tuple)
            #
            # here we have done analysis for all reference files and ONE analysis file.
            # We generate the dataframe and write it out.
            #
            similarity_df = pd.DataFrame(
                data=resultlist,
                columns=["ana_tag", "ana_text", "similarity", "ref_tag", "ref_text"],
            )
            #
            # serialize dataframe in the joblib format.
            # Always write an Excel sheet in addition where
            # the filename ending is "self.tag.xlsx"
            #
            g = self.writer.write_result_file(
                similarity_df,
                root=os.path.join(project, RESFOLDERNAME),
                # name=".".join([anafile, reffile]),
                name=anafile,
                tag=self.tag,
            )
            #
            # add generated files as their names to the file list returned to caller.
            #
            generated_files += g

        s = Status.SUCCESS
        m = f"{project} analysis done."
        d = {"generated_files": generated_files}
        return s, m, d
