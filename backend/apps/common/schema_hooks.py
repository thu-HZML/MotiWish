def exclude_internal_endpoints(endpoints):
    excluded_prefixes = ("/api/schema/", "/api/docs/")
    filtered = []
    for path, path_regex, method, callback in endpoints:
        if path.startswith(excluded_prefixes):
            continue
        filtered.append((path, path_regex, method, callback))
    return filtered
