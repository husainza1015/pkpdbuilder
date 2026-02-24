/**
 * Literature search tools — PubMed + PKPDBuilder drug lookup
 * Author: Husain Z Attarwala, PhD
 */

import https from 'https';

function httpsGet(url: string): Promise<string> {
  return new Promise((resolve, reject) => {
    https.get(url, (res) => {
      let data = '';
      res.on('data', (chunk) => (data += chunk));
      res.on('end', () => resolve(data));
      res.on('error', reject);
    }).on('error', reject);
  });
}

export async function searchPubmed(query: string, maxResults: number = 5): Promise<any> {
  try {
    const searchUrl = `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=${encodeURIComponent(query)}&retmax=${maxResults}&retmode=json`;
    const searchData = JSON.parse(await httpsGet(searchUrl));
    const ids = searchData?.esearchresult?.idlist || [];

    if (ids.length === 0) {
      return { success: true, count: 0, results: [] };
    }

    const fetchUrl = `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id=${ids.join(',')}&retmode=json`;
    const fetchData = JSON.parse(await httpsGet(fetchUrl));

    const results = ids.map((id: string) => {
      const article = fetchData?.result?.[id];
      if (!article) return null;
      return {
        pmid: id,
        title: article.title,
        authors: (article.authors || []).map((a: any) => a.name).slice(0, 3),
        journal: article.source,
        year: article.pubdate?.split(' ')[0],
        doi: (article.elocationid || '').replace('doi: ', ''),
      };
    }).filter(Boolean);

    return { success: true, count: results.length, results };
  } catch (err: any) {
    return { success: false, error: err.message };
  }
}

export async function lookupDrug(drugName: string): Promise<any> {
  try {
    const url = `https://www.pkpdbuilder.com/api/v1/drug-lookup?name=${encodeURIComponent(drugName)}`;
    const data = await httpsGet(url);
    return JSON.parse(data);
  } catch (err: any) {
    return { success: false, error: err.message };
  }
}
