class VisualizerInterface():
    """
    Interface class invoking corresponding 
    visualizer class
    """

    def __init__(self, Visualizer_class):
        self.visualizer = Visualizer_class()
        return

    def visualize_project(self, project):
        s, m, d = self.visualizer.visualize_project(project)
        return s, m, d
