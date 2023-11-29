# Agenda Analytics 


## Introduction


#### 📝 Description

Agenda Analytics has the matching of given agendas to the activities of companies and public administration as its content. The obtained matching scores can be used for detailed reporting and visualization.
(Agendas of interest could not only be the sustainable development goals (SDGs) or environmental social governance risks in banks (ESGs) but also e. g. the public governance codex, addressing the emerging interest on governance topics in public companies. Additionally any interested party could develop their own agenda, summarizing key aspects to them, under which they intend to analyse companies of interest.)

#### 🏆 Value Proposition

This application leverages public data to generate value for the public, by extracting information needed for an automatic assesment of the given agenda. Therefor the public gains access to knowledge, which wasnt available before. Additionally the application shows the added value that can be generated by crawling availbale webdocuments.



#### 🎯 End User Frontend

💡 Sustainable Development Goals              |  💡 Environmental Social Governance 
:-------------------------:|:-------------------------:
<img align="center" alt="SDG case study" width="100%" src="https://raw.githubusercontent.com/SALTED-Project/AgendaAnalytics/master/info/casestudies/Folie2.JPG" />  |  <img align="center" alt="ESG case study" width="100%" src="https://raw.githubusercontent.com/SALTED-Project/AgendaAnalytics/master/info/casestudies/Folie3.JPG" />

💡 Artificial Intelligence Strategy of the Federal Government Germany              |  💡 European Molecular Biology Labaratory Programme 2022-2026
:-------------------------:|:-------------------------:
<img align="center" alt="KI case study" width="100%" src="https://raw.githubusercontent.com/SALTED-Project/AgendaAnalytics/master/info/casestudies/Folie4.JPG" /> | <img align="center" alt="KI case study" width="100%" src="https://raw.githubusercontent.com/SALTED-Project/AgendaAnalytics/master/info/casestudies/Folie5.JPG" />

#### 🚀 Agenda Analytics User Flow

<img align="center" alt="Workflow" width="50%" src="https://raw.githubusercontent.com/SALTED-Project/AgendaAnalytics/master/info/casestudies/Folie1.JPG" />


#### 📧 Contact Information

This application was developed by Kybeidos GmbH (contact: team@agenda-analytics.eu)


## Infrastructure

The above use case is realized by the following services.
The documentation for each single service can be found in the corresponding service directories (see: ``./services``):

* [AgendaAnalytics-Commons](https://github.com/SALTED-Project/AgendaAnalytics/blob/master/services/AgendaAnalytics-Commons/README.rst)
* [AgendaAnalytics-DiscoverAndStore](https://github.com/SALTED-Project/AgendaAnalytics/blob/master/services/AgendaAnalytics-DiscoverAndStore/README.rst)
* [AgendaAnalytics-Mapping](https://github.com/SALTED-Project/AgendaAnalytics/blob/master/services/AgendaAnalytics-Mapping/README.rst)
* [AgendaAnalytics-Publish](https://github.com/SALTED-Project/AgendaAnalytics/blob/master/services/AgendaAnalytics-Publish/README.rst)
* [AgendaAnalytics-Crawling](https://github.com/SALTED-Project/AgendaAnalytics/blob/master/services/AgendaAnalytics-Crawling/README.rst)
* [AgendaAnalytics-AgendaMatching](https://github.com/SALTED-Project/AgendaAnalytics/blob/master/services/AgendaAnalytics-AgendaMatching/README.rst)
* [AgendaAnalytics-SimCore](https://github.com/SALTED-Project/AgendaAnalytics/blob/master/services/AgendaAnalytics-SimCore/README.rst)
* [AgendaAnalytics-SearchEngine](https://github.com/SALTED-Project/AgendaAnalytics/blob/master/services/AgendaAnalytics-SearchEngine/README.rst)

    * own google api key needed

* [AgendaAnalytics-FileServer](https://github.com/SALTED-Project/AgendaAnalytics/blob/master/services/AgendaAnalytics-FileServer/README.rst)
* [AgendaAnalytics-VDPP](https://github.com/SALTED-Project/AgendaAnalytics/blob/master/services/AgendaAnalytics-VDPP/README.rst)

    * dockerhub pull acces for kybeidosci repo needed (access tokens will be granted by Kybeidos GmbH: team@agenda-analytics.eu)      

* [AgendaAnalytics-MQTTtrigger](https://github.com/SALTED-Project/AgendaAnalytics/blob/master/services/AgendaAnalytics-MQTTtrigger/README.rst)

Additionally you need:
* Own setup of NGSI-LD Scorpio Broker
* Own setupof MQTT Broker


An exemplary setup / deployment would be:

* e.g. Service Setup: 

    <img align="center" alt="Agenda Analytics services setup" width="80%" src="https://raw.githubusercontent.com/SALTED-Project/AgendaAnalytics/master/info/infrastructure/services_setup.JPG" />

* e.g. Deployment Order:        

    <img align="center" alt="Agenda Analytics services deployment order" width="50%" src="https://raw.githubusercontent.com/SALTED-Project/AgendaAnalytics/master/info/infrastructure/services_deploymentorder.JPG" />


This enables the following Data Injection and Enrichment Toolchain:

* e.g. DIT:        

    <img align="center" alt="Agenda Analytics DIT" width="50%" src="https://raw.githubusercontent.com/SALTED-Project/AgendaAnalytics/master/info/infrastructure/dit_example.JPG" />

* e.g. DET:        

    <img align="center" alt="Agenda Analytics DET" width="50%" src="https://raw.githubusercontent.com/SALTED-Project/AgendaAnalytics/master/info/infrastructure/det_example.JPG" />


The services referenced above result in the following enduser application:

* **MapServer**

    * https://agenda-map.hdkn.eu --> Sustainable Development Goals (deutsch) - Kurzfassung    
    * Current links are:

        * [Environmental Social Governance (deutsch) - by ChatGPT](https://agenda-map.hdkn.eu/urn:ngsi-ld:DistributionDCAT-AP:f7c6cdd0-3b55-412d-a3d9-0c0fef06fdfd.html)
        * [Strategie Künstliche Intelligenz der Bundesregierung, Fortschreibung 2020](https://agenda-map.hdkn.eu/urn:ngsi-ld:DistributionDCAT-AP:58e6963c-75af-485c-8f6c-562d3f2b987a.html)
        * [Sustainable Development Goals (deutsch) - Kurzfassung](https://agenda-map.hdkn.eu/urn:ngsi-ld:DistributionDCAT-AP:9bd03954-fa71-4fd7-a014-77b79b6534a0.html)
        * [Extract from The EMBL Programme 2022–2026 (engish)](https://agenda-map.hdkn.eu/urn:ngsi-ld:DistributionDCAT-AP:c2777763-805e-4e9d-a2de-efea99c6a397.html)

    * the exemplary implementation code can be found in the ``./application`` directory: [AgendaAnalytics-MapServer](https://github.com/SALTED-Project/AgendaAnalytics/blob/master/application/AgendaAnalytics-MapServer/README.rst)



    

## License

All services use the MIT license:

    ```
    MIT License

    Copyright (c) 2023 Kybeidos GmbH

    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction, including without limitation the rights
    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in all
    copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    SOFTWARE.
    ```


Licenses by packages used within AgendaAnalytics are:

* MIT License
* Historical Permission Notice and Disclaimer (HPND)
* Apache Software License
* BSD License
* Mozialle Public License 2.0 (MPL 2.0)
* GNU Library or Lesser General Public License (LGPL)
* Eclipse Public License v2.0 / Eclipse Distribution License
* ISC
* BSD-3-Clause
* Python Software License
* Zope Public License


## Acknowledgement
This work was supported by the European Commission CEF Programme by means of the project SALTED ‘‘Situation-Aware Linked heTerogeneous Enriched Data’’ under the Action Number 2020-EU-IA-0274.


