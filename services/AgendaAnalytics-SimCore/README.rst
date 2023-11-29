*******************************************
SALTED service: Simcore
*******************************************


A polished, token-controlled text similarity module based on Transformers




Deployment
#############################################

For deploying using docker:
    
    .. code-block::
        
        # adapt docker-compose.yaml if needed
        # inside root directory where docker-compose.yaml is
        docker-compose -p salted_simcore up -d --build

Visit API doc: http://localhost:9060/docs#/



General Workflow
#############################################

* open task and obtain token with ``/open_task`` endpoint
* upload your analysis text (e.g. company text regarding sustainability) wit ``/upload_text/{token}`` endpoint
* upload your reference text (e.g. sustainability report) wit ``/upload_reference/{token}`` endpoint
* choose your analyzer of choice (coarse-performes text based matching, detailed-performs sentence based matching) with ``/set_analyzer/{token}`` endpoint
* perform the analysis with ``/analyze_project/{token}`` endpoint
* choose your vizualization of choice (heatmap, barplot, scatterplot) with ``/set_visualizer/{token}`` endpoint
* perform the vizualization with ``/visualize_project/{token}`` endpoint
* list all the task files with ``/list_task_files/{token}`` endpoint
* download the results with ``/download_file/{token}`` endpoint using the file name from the list of task files as parameter