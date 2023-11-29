import os
import logging
import joblib
import pandas as pd

logger = logging.getLogger(os.path.basename(__file__))


class Resultwriter:
    """
    Class provides methods for writing out similarity results
    """

    def __init__(self):
        return

    def write_result_file(
        self, rdf: pd.DataFrame, root=".", name="result", tag="generic"
    ):
        local_filename_list = []
        #
        # form outputfilename
        #
        outfilename = ".".join([name, tag])
        outfile = os.path.join(root, outfilename)
        #
        # write out serialized data in joblib format
        #
        joblib.dump(rdf, outfile)
        local_filename_list.append(outfile)
        #
        # in addition, write out an excel sheet
        # For this append the "xlsx" tag to the output file name
        #
        outfile = outfile + ".xlsx"
        rdf.to_excel(outfile, sheet_name="Similarity_result", engine="xlsxwriter")
        local_filename_list.append(outfile)

        return local_filename_list  # return full path of generated file as list.
