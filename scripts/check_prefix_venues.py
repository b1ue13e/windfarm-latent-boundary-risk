import re

with open('references.bib', 'r', encoding='utf-8') as f:
    text = f.read()

entries = re.findall(r'@(\w+)\{([^,]+),\s*(.*?)\n\}', text, re.DOTALL)
print(f"Total bib entries: {len(entries)}")

prefix_venue_rules = {
    '10.1016': ['Applied Energy', 'Energy', 'Journal of Computational Physics', 'Renewable and Sustainable Energy Reviews', 'Future Generation Computer Systems'],
    '10.1109': ['IEEE Transactions on Knowledge and Data Engineering', 'IEEE Transactions on Power Systems', 'IEEE Transactions on Smart Grid', 'IEEE Transactions on Industrial Informatics', 'IEEE Control Systems Magazine', 'IEEE Transactions on Sustainable Energy'],
    '10.1002': ['Wind Energy', 'Quarterly Journal of the Royal Meteorological Society'],
    '10.1038': ['Nature Reviews Physics', 'Scientific Data'],
    '10.1103': ['PRX Energy'],
    '10.1007': ['Springer', 'Discover Applied Sciences'],
    '10.2172': ['National Renewable Energy Laboratory', 'National Renewable Energy Laboratory (NREL)'],
    '10.1115': ['Journal of Solar Energy Engineering'],
    '10.24963': ['Proceedings of the 27th International Joint Conference on Artificial Intelligence (IJCAI)', 'Proceedings of the 28th International Joint Conference on Artificial Intelligence (IJCAI)'],
    '10.1609': ['Proceedings of the AAAI Conference on Artificial Intelligence'],
    '10.1145': ['Proceedings of the 26th ACM SIGKDD International Conference on Knowledge Discovery and Data Mining'],
    '10.1049': ['IET Renewable Power Generation'],
    '10.1214': ['Statistical Science'],
    '10.1162': ['Neural Computation'],
    '10.5194': ['Wind Energy Science']
}

mismatches = 0
for et, key, body in entries:
    doi_m = re.search(r'doi\s*=\s*\{([^\}]+)\}', body)
    venue_m = re.search(r'(journal|booktitle|publisher|institution)\s*=\s*\{([^\}]+)\}', body)
    doi = doi_m.group(1).strip() if doi_m else None
    venue = venue_m.group(2).strip() if venue_m else ''
    
    if doi:
        prefix = doi.split('/')[0]
        allowed_venues = prefix_venue_rules.get(prefix, [])
        if allowed_venues and not any(v.lower() in venue.lower() or venue.lower() in v.lower() for v in allowed_venues):
            print(f"[MISMATCH] {key:25} | Prefix {prefix} not expected for venue: \"{venue}\" (DOI: {doi})")
            mismatches += 1
        else:
            print(f"[VALID]    {key:25} | {venue[:25]:25} | {doi}")
    else:
        print(f"[NO-DOI]   {key:25} | {venue[:25]:25}")

print(f"\nTotal prefix mismatches found: {mismatches}")
