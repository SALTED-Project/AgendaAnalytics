import os
import logging
import joblib
import seaborn as sns
import matplotlib.pylab as plt

from dynaconf import settings
from simcore_api_schema_mod import Status
from visualizers.abstract_visualizer_mod import AbstractVizualizer


RESFOLDERNAME = settings.RESFOLDERNAME
PROCESSABLE = "detailed"   # this is the filetag for files whose content can be visualized here

logger = logging.getLogger(os.path.basename(__file__))

class DetailedVisualizer(AbstractVizualizer):

    def __init__(self):
        logger.info(str(self.__class__.__name__) +  " initialized")
        return

    #
    # this routine must be implemented and does the specific rendering
    #
    def visualize_project(self, project: str):

        def charlim(s):
            return s[:25]

        generated_files = []
        result_folder = os.path.join(project, RESFOLDERNAME)
        foundfile = False

        for f in os.listdir(result_folder):

            if f.endswith(PROCESSABLE):
                foundfile = True
                print(f)
                #
                # recover first and second part of the filename
                #
                f1f2 = f.split("."+PROCESSABLE)[0]
                f1, f2 = f1f2.split("$")

                #
                # load corresponding dataframe
                # and sort with respect to reference texts
                # (important for concat!)
                #
                df = joblib.load(os.path.join(result_folder, f))
                #
                # *** Pitfall ***
                #
                # We end up with horrible crashs if we do not truncate the
                # generic row and column labeling for the 2D visualization!
                # Seaborn automatically uses the dataframe indices and dataframe
                # column names as labelings in the plot! We therefore must
                # truncate them accordingly.
                #
                df.index = map(charlim, df.index)
                df.columns = map(charlim, df.columns)
                #
                # generate seaborn 2D heatmap
                #
                plt.figure(figsize = (16,10))
                ax = sns.heatmap(df, cmap='Greens', linewidths=0.5, annot=True)
                plt.title('2D heatmap of similarities', fontsize = 15)
                plt.xlabel('Reference text: '+f2, fontsize = 15)
                plt.ylabel('Analysis text: '+f1, fontsize = 15)
                #
                # generate filename from fragments and save graph to disk
                #
                tref_outfile = "$".join([f1, f2]) + ".2D_heatmap.png"
                tref_outfile = os.path.join(result_folder, tref_outfile)
                ax.figure.savefig(tref_outfile, dpi=600, bbox_inches='tight')
                generated_files.append(tref_outfile)

        s = Status.SUCCESS
        if foundfile:
            m = f"Visualizations done."
        else:
            m = f"No {PROCESSABLE} data found for visualization."
        d = {"generated_files": generated_files}
        return s, m, d