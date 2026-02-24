"""Literature and reference data tools."""
import json
import os
from .registry import register_tool


@register_tool(
    name="search_pubmed",
    description="Search PubMed for pharmacokinetic/pharmacometric publications. Returns titles, authors, PMIDs, and abstracts. Useful for finding published PopPK models, parameter references, and covariate effects.",
    parameters={
        "properties": {
            "query": {"type": "string", "description": "Search query (e.g., 'vancomycin population pharmacokinetics')"},
            "max_results": {"type": "integer", "description": "Maximum results to return", "default": 10}
        },
        "required": ["query"]
    }
)
def search_pubmed(query: str, max_results: int = 10) -> dict:
    import urllib.request
    import urllib.parse
    import xml.etree.ElementTree as ET
    
    try:
        # Step 1: Search for PMIDs
        search_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={urllib.parse.quote(query)}&retmax={max_results}&retmode=json"
        with urllib.request.urlopen(search_url, timeout=15) as resp:
            search_data = json.loads(resp.read())
        
        pmids = search_data.get("esearchresult", {}).get("idlist", [])
        if not pmids:
            return {"success": True, "results": [], "message": "No results found"}
        
        # Step 2: Fetch summaries
        ids = ",".join(pmids)
        fetch_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={ids}&retmode=json"
        with urllib.request.urlopen(fetch_url, timeout=15) as resp:
            fetch_data = json.loads(resp.read())
        
        results = []
        for pmid in pmids:
            article = fetch_data.get("result", {}).get(pmid, {})
            if not article:
                continue
            authors = [a.get("name", "") for a in article.get("authors", [])[:3]]
            results.append({
                "pmid": pmid,
                "title": article.get("title", ""),
                "authors": authors,
                "journal": article.get("source", ""),
                "year": article.get("pubdate", "")[:4],
                "doi": next((id_val["value"] for id_val in article.get("articleids", []) if id_val.get("idtype") == "doi"), None),
            })
        
        return {"success": True, "count": len(results), "results": results}
    
    except Exception as e:
        return {"success": False, "error": str(e)}


@register_tool(
    name="lookup_drug",
    description="Look up published PK parameters for a drug from the PKPDBuilder database. Returns population PK model parameters (CL, V, Ka, etc.), model type, and source reference.",
    parameters={
        "properties": {
            "drug_name": {"type": "string", "description": "Drug name (generic or brand)"}
        },
        "required": ["drug_name"]
    }
)
def lookup_drug(drug_name: str) -> dict:
    import urllib.request
    import urllib.parse
    
    try:
        url = f"https://www.pkpdbuilder.com/api/v1/search?q={urllib.parse.quote(drug_name)}"
        req = urllib.request.Request(url, headers={"User-Agent": "pmx-cli/0.1"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        
        if data.get("results"):
            return {"success": True, "drug": drug_name, "results": data["results"][:5]}
        return {"success": True, "drug": drug_name, "results": [], "message": "No published models found"}
    
    except Exception as e:
        return {"success": False, "error": str(e)}
