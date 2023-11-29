import os
import logging
import joblib
import pandas as pd
import seaborn as sns
import matplotlib.pylab as plt

from dynaconf import settings
from simcore_api_schema_mod import Status
from visualizers.abstract_visualizer_mod import AbstractVizualizer


RESFOLDERNAME = settings.RESFOLDERNAME
PROCESSABLE = "coarse" # this is the filetag for files whoso content can be visualized here
REQUIRED_COLS = ["ana_tag", "ana_text", "ref_tag", "ref_text", "similarity"]

logger = logging.getLogger(os.path.basename(__file__))

class CoarseVisualizer(AbstractVizualizer):

    def __init__(self):
        logger.info(str(self.__class__.__name__) +  " initialized")
        return
    

    @staticmethod
    def checkcolumns(df:pd.DataFrame) -> bool:
        """
        make sure that all columns required for a coarse
        treatment are contained in the data frame
        """
        if all([x in REQUIRED_COLS for x in df.columns]):
            return True
        return False

    #
    # this routine must be implemented and does the specific rendering
    #
    def visualize_project(self, project: str):

        generated_files = []
        result_folder = os.path.join(project, RESFOLDERNAME)
        foundfile = False
        cdf = pd.DataFrame()

        for f in os.listdir(result_folder):

            if f.endswith(PROCESSABLE):
                foundfile = True
                print(f)
                #
                # load corresponding dataframe
                # and sort with respect to reference texts
                # (important for concat!)
                #
                df = joblib.load(os.path.join(result_folder, f))
                if not self.checkcolumns(df):
                    s = Status.FAILED
                    m = "** Internal error in coarse visualizer. Check data table."
                    d = {"generated_files": []}
                    return s, m, d

                df = df.sort_values("ref_tag")
                df = df.drop(columns=["ana_text", "ref_text"])
                #
                # generate a bar plot for this specific file
                # tref contains the name of the current analysis text
                #
                tref = str(df["ana_tag"].loc[0])
                tref_outfile = os.path.join(result_folder, tref + ".png")
                ax = df.plot.bar(x="ref_tag", y="similarity", 
                                title=f"Coarse similarities for text {tref}", 
                                xlabel="Reference texts",
                                ylabel="Similarity",
                                legend=None)
                #
                # save original bar plot
                #
                ax.figure.savefig(tref_outfile, dpi=600, bbox_inches='tight')
                generated_files.append(tref_outfile)
                #
                # rearrange and eliminate parts of the df making it suitable
                # for concatenation
                #
                df = df.rename(columns={"similarity":tref})
                df = df.drop(columns=["ana_tag"])
                df.index = df["ref_tag"]
                df = df.drop(columns=["ref_tag"])
                #
                # form the larger dataframe for a 2D heatmap
                #
                cdf = pd.concat([cdf, df], axis="columns")
        #
        # plot 2D heatmap of text similarities
        # if there were data to visualize
        #
        if foundfile:
            ax = sns.heatmap(cdf.T, cmap='Greens', linewidths=0.5, annot=True)
            plt.title('2D heatmap of similarities', fontsize = 15)
            plt.xlabel('Reference texts', fontsize = 15)
            plt.ylabel('Analysis texts', fontsize = 15)
            tref_outfile = os.path.join(result_folder, "2D_heatmap.png")
            ax.figure.savefig(tref_outfile, dpi=600, bbox_inches='tight')
            generated_files.append(tref_outfile)

        s = Status.SUCCESS
        if foundfile:
            m = f"Visualizations done."
        else:
            m = f"No {PROCESSABLE} data found for visualization."
        d = {"generated_files": generated_files}
        return s, m, d