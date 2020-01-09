import requests
from bs4 import BeautifulSoup
import dropbox
from datetime import date, timedelta
import json
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk import pos_tag
import logging

logging.basicConfig(filename='FERC.log', level=logging.DEBUG)

# class contains all methods
class FercSpider:
    # initialization
    def __init__(self, **kwargs):
        # base url to POST search query form
        self.url = 'https://elibrary.ferc.gov/idmws/search/advResults.asp'

        # download url for getting PDFs
        self.downloadurl = 'https://elibrary.ferc.gov/idmws'

        # search terms imported from file
        with open('srchterms.json', 'r') as f:
            self.search_terms = json.load(f)
        # formatting terms as string for form POST
        sep = ' OR '
        self.text_search = sep.join(self.search_terms)

        # initialize other keyword arguments
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

    # method executes POST request w/ form data and returns html response
    def make_request(self):
        # form containing search parameters
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

        logging.info('Making request to url: {}'.format(self.url))
        header = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_0) AppleWebKit/537.36 (KHTML, like Gecko)'}

        # POST request and get response
        response = requests.post(self.url, data=formdata, timeout=600, headers=header)

        print('Request completed with code:{}'.format(response.status_code))
        logging.info('Request completed with code:{}'.format(response.status_code))
        return response

    # parse the search results page
    def parse(self, **kwargs):
        # make request
        response = self.make_request()

        # parsing done with BeautifulSoup library
        soup = BeautifulSoup(response.content, 'html5lib')

        # get num search results
        try:
            num_hits = soup.select('td tr + tr strong')[0].text
        except:
            num_hits = 0
        logging.info('Search returned {} hits'.format(num_hits))

        # filter table rows from result, extract file description for save name in dropbox
        download_links = []
        if int(num_hits) != 0:
            rows = soup.select('body > center > table > tbody > tr')[9:-2]
            for ix, row in enumerate(rows):
                try:
                    text = row.select('td')[3].text.replace('\n', '')
                except:
                    text = ""

                # find search term matches in file description using NLTK
                term = [t for t in self.search_terms if t in text]
                if len(term) > 0:
                    term = term[0]
                    filtered = text.replace(term, '')
                    words = word_tokenize(filtered)
                    nnp = [x[0] for x in pos_tag(words) if x[1] == 'NNP'][:5]
                    s = '-'
                    nnp_str = s.join(nnp)
                    title = '{}_{}'.format(term,nnp_str)
                else:
                    words = word_tokenize(text)
                    nnp = [x[0] for x in pos_tag(words) if x[1] == 'NNP'][:5]
                    s = '-'
                    title = s.join(nnp)
                # now that we have a title, get the link and append both to download_links as tuple
                try:
                    path = row.find('a', href=True, text='FERC Generated PDF')['href']
                    path = self.downloadurl + path.replace('..', '')
                    print(path)
                    print(title)
                    download_links.append((title, path))
                except TypeError:
                    logging.warning('No FERC PDFs available for index: {}'.format(ix))
                    try:
                        path = row.find('a', href=True, text='PDF')['href']
                        path = self.downloadurl + path.replace('..', '')
                        print(path)
                        print(title)
                        download_links.append((title, path))
                    except TypeError:
                        logging.warning('No PDFs available for index: {}'.format(ix))
                        print(row)
        else:
            logging.warning('Search returned 0 hits')
        return download_links, response

    # upload files to dropbox
    @staticmethod
    def upload_dropbox(links, r, **kwargs):
        # get API token
        with open('token.txt', 'r') as file:
            access_token = file.read()
        today = date.today().strftime("%m/%d/%Y").replace('/', '-')
        path = '/{}/'.format(today)
        # connect to dropbox
        dbx = dropbox.Dropbox(access_token)

        # save response HTML to dropbox
        if kwargs.get('saveHTML'):
            logging.info('Begin save page HTML')
            savestr = path + '{}_HTML.html'.format(today)
            try:
                dbx.files_upload(r.content, savestr)
                logging.info('Upload complete. filename:{}'.format(savestr))
            except Exception as e:
                logging.warning('Error downloading HTML.\nException: {}'.format(e))
                print('Upload Failed html', e)

        # follow download links and upload result with proper title
        for ix, link in enumerate(links):
            name = link[0] + '.pdf'
            pdf_path = '/{}/{}'.format(today,name)
            try:
                dl_response = requests.get(link[1])
                logging.info('Successfully downloaded file URL: {}'.format(link[1]))
                print('response success')
            except Exception as e:
                logging.warning('Error downloading file URL: {}\nException: {}'.format(link[1], e))
                print('response failed')
                continue
            try:
                dbx.files_upload(dl_response.content, pdf_path)
                logging.info('Successfully uploaded to dropbox: {}'.format(pdf_path))
                print('upload success')
            except Exception as e:
                logging.warning('Error uploading to dropbox: {}\nException: {}'.format(link[1], e))
                print('upload failed')
                continue

# main function
if __name__ == "__main__":
    logging.info('BEGIN')
    fercSpider = FercSpider(docClass='Applicant Correspondence')
    linksList, res = fercSpider.parse()
    FercSpider.upload_dropbox(linksList, res, saveHTML=True)
    logging.info('END')
    print('END')
