import requests
from bs4 import BeautifulSoup
import dropbox
from datetime import date, timedelta
import os
import logging
logging.basicConfig(filename='FERC.log', level=logging.DEBUG)


class FercSpider:
    def __init__(self, **kwargs):
        self.url = 'https://elibrary.ferc.gov/idmws/search/advResults.asp'
        self.downloadurl = 'https://elibrary.ferc.gov/idmws'
        if kwargs.get('fromDate'):
            self.from_date = kwargs['fromDate']
        else:
            self.from_date = (date.today() - timedelta(days=7)).strftime("%m/%d/%Y")
        if kwargs.get('toDate'):
            self.to_date = kwargs['toDate']
        else:
            self.to_date = date.today().strftime("%m/%d/%Y")
        if kwargs.get('docClass'):
            self.doc_class = kwargs['docClass']
        else:
            self.doc_class = ''
        if kwargs.get('textSearch'):
            self.text_search = kwargs['textSearch']
        else:
            self.text_search = '"Project Safety-Related Submission" OR \
                                "EAP Annual Update" OR \
                                "Annual Spillway Gate Operation" OR \
                                "Public Safety Plan" OR \
                                "Signage" OR \
                                "Annual Downstream Assessment" OR \
                                "EAP Exemption" OR \
                                "Log Boom" OR \
                                "Boat Barrier" OR \
                                "Buoy" OR \
                                "BGS" OR \
                                "Salmonids" OR \
                                "Fish Guidance" OR \
                                "Dam Safety Inspection" OR \
                                "Emergency Action Plan" OR \
                                "Safety Signs" OR \
                                "Safety Signage"'
            print(self.text_search)

    def make_request(self):
        formdata = [
            ('FROMdt', ''),
            ('TOdt', ''),
            ('fromDocDate', ''),
            ('toDocDate', ''),
            ('fromPosDate', ''),
            ('toPosDate', ''),
            ('firstDt', '1/1/1904'),
            ('LastDt', '12/31/2037'),
            ('DocsStart', '0'),
            ('DocsLimit', '200'),
            ('SortSpec', 'filed_date desc accession_num asc'),
            ('category', 'submittal'),
            ('category', 'issuance'),
            ('filed_date', 'on'),
            ('from_date', self.from_date),
            ('to_date', self.to_date),
            ('from_dDate', self.from_date),
            ('to_dDate', self.to_date),
            ('from_pDate', self.from_date),
            ('to_pDate', self.to_date),
            ('docket1', ''),
            ('subdocket1', ''),
            ('docket2', ''),
            ('subdocket2', ''),
            ('docket3', ''),
            ('subdocket3', ''),
            ('docket4', ''),
            ('subdocket4', ''),
            ('library', 'hydro'),
            ('textsearch', self.text_search),
            ('description', 'description'),
            ('fulltext', 'fulltext'),
            ('class', self.doc_class),
            ('class', '999'),
            ('class', '999'),
            ('class', '999'),
            ('type', '999'),
            ('type', '999'),
            ('type', '999'),
            ('type', '999'),
            ('AffilTP1', ''),
            ('AffilAF1', ''),
            ('AffilLastName1', ''),
            ('AffilFirstName1', ''),
            ('AffilMidName1', ''),
            ('AffilTP2', ''),
            ('AffilAF2', ''),
            ('AffilLastName2', ''),
            ('AffilFirstName2', ''),
            ('AffilMidName2', ''),
            ('AffilTP3', ''),
            ('AffilAF3', ''),
            ('AffilLastName3', ''),
            ('AffilFirstName3', ''),
            ('AffilMidName3', ''),
            ('AffilTP4', ''),
            ('AffilAF4', ''),
            ('AffilLastName4', ''),
            ('AffilFirstName4', ''),
            ('AffilMidName4', ''),
            ('fed_reg_cite', ''),
            ('fed_court_cite', ''),
            ('ferc_cite', ''),
            ('accession_num', ''),
            ('opinion', ''),
            ('ordernum', ''),
            ('child_doc', ''),
            ('availability', 'p'),
            ('DocsCount', '200'),
            ]

        # Make the request
        logging.info('Making request to url: {}'.format(self.url))
        header = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_0) AppleWebKit/537.36 (KHTML, like Gecko)'}
        response = requests.post(self.url, data=formdata, timeout=600, headers=header)
        print('Request completed with code:{}'.format(response.status_code))
        logging.info('Request completed with code:{}'.format(response.status_code))
        return response

    def parse(self, **kwargs):
        response = self.make_request()
        soup = BeautifulSoup(response.content, 'html5lib')
        num_hits = soup.select('td tr + tr strong')[0].text
        logging.info('Search returned {} hits'.format(num_hits))
        download_links = []
        if int(num_hits) != 0:
            rows = soup.select('body > center > table > tbody > tr')[9:-2]
            for ix, row in enumerate(rows):
                try:
                    path = row.find('a', href=True, text='FERC Generated PDF')['href']
                    path = self.downloadurl + path.replace('..', '')
                    print(path)
                    download_links.append(path)
                except TypeError:
                    logging.warning('No FERC PDFs available for index: {}'.format(ix))
                    try:
                        path = row.find('a', href=True, text='PDF')['href']
                        path = self.downloadurl + path.replace('..', '')
                        print(path)
                        download_links.append(path)
                    except TypeError:
                        logging.warning('No PDFs available for index: {}'.format(ix))
                        print(row)
        else:
            logging.warning('Search returned 0 hits')
        return download_links, response

    @staticmethod
    def upload_dropbox(links, r, **kwargs):
        with open("token.txt", 'r') as f:
            access_token = f.read()
            print(access_token)
            quit()

        today = date.today().strftime("%m/%d/%Y").replace('/', '-')
        dbx = dropbox.Dropbox(access_token)
        path = '/{}/'.format(today)

        if kwargs.get('saveHTML'):
            logging.info('Begin save page HTML')
            savestr = path + '{}_HTML.html'.format(today)
            try:
                dbx.files_upload(r.content, savestr)
                logging.info('Upload complete. filename:{}'.format(savestr))
            except:
                print('Upload Failed html')

        for ix, link in enumerate(links):
            fileID = link.split('=')[-1]
            name = today + '_' + fileID + '.pdf'
            pdf_path = '/{}/{}'.format(today,name)
            try:
                dl_response = requests.get(link)
                logging.info('Successfully downloaded file URL: {}'.format(link))
                print('response success')
            except:
                logging.warning('Error downloading file URL: {}'.format(link))
                print('response failed')
                continue
            try:
                dbx.files_upload(dl_response.content, pdf_path)
                logging.info('Successfully uploaded to dropbox: {}'.format(pdf_path))
                print('upload success')
            except :
                logging.warning('Error uploading to dropbox: {}'.format(link))
                print('upload failed')
                continue


if __name__ == "__main__":
    logging.info('BEGIN')
    fercSpider = FercSpider(docClass='Applicant Correspondence')
    linksList, res = fercSpider.parse()
    FercSpider.upload_dropbox(linksList, res, saveHTML=True)
    logging.info('END')
    print('END')
