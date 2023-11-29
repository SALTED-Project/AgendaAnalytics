class HandlerInterface():
    """
    Interface class invoking corresponding analysis module
    """

    def __init__(self, NLP_handler):
        self.nlp_handler = NLP_handler()
        return

    def analyze_project(self, project):
        s, m, d = self.nlp_handler.analyze_project(project)
        return s, m, d