import requests
import csv
from time import sleep, time
# Your Comic Vine API key
api_key = 'YOU API'
# Replace 'Big Comic Spirits' with the name of the series you're searching for
series_name_query = 'Big Comic Spirits'
# Set a delay between requests to handle rate limiting
rate_limit_delay = 20

endpoint_usage = {
    '/search': {'count': 0, 'reset_time': time() + 3600},
    '/volume': {'count': 0, 'reset_time': time() + 3600},
    '/issues': {'count': 0, 'reset_time': time() + 3600},
    '/issue': {'count': 0, 'reset_time': time() + 3600},
}

def make_request(url, headers, params):
    global endpoint_usage  # Ensure we're modifying the global variable
    # Extract the endpoint from the URL
    endpoint = '/' + url.split('.com/api')[1].split('/')[1]

    # Rate limiting check and wait
    usage = endpoint_usage[endpoint]
    current_time = time()
    if current_time >= usage['reset_time']:
        usage['count'] = 0
        usage['reset_time'] = current_time + 3600

    if usage['count'] >= 200:
        sleep_time = usage['reset_time'] - current_time
        print(f"Rate limit reached for {endpoint}. Waiting {sleep_time} seconds.")
        sleep(sleep_time)
        usage['count'] = 0
        usage['reset_time'] = time() + 3600

    # Corrected to use requests.get instead of make_request recursively
    response = requests.get(url, headers=headers, params=params)
    usage['count'] += 1

    return response

def search_series(api_key, query):
    base_url = 'https://comicvine.gamespot.com/api/search'
    headers = {'User-Agent': 'PythonApp'}
    params = {
        'api_key': api_key,
        'query': query,
        'resources': 'volume',
        'format': 'json',
        'field_list': 'id,name',
        'limit': 1 
    }
    response = make_request(base_url, headers=headers, params=params)
    response.raise_for_status() 
    return response.json()['results'][0]['id']

def fetch_all_issues_for_series(api_key, series_id):
    issues = []
    offset = 0
    limit = 100 
    total_results = 1  # Initialize with a dummy value to enter the loop

    while offset < total_results:
        base_url = f'https://comicvine.gamespot.com/api/issues/'
        headers = {'User-Agent': 'PythonApp'}
        params = {
            'api_key': api_key,
            'filter': f'volume:{series_id}',
            'format': 'json',
            'field_list': 'id',
            'limit': limit,
            'offset': offset
        }
        response = make_request(base_url, headers=headers, params=params)
        response.raise_for_status() 

        data = response.json()
        total_results = data['number_of_total_results']
        issues.extend(data['results'])
        offset += data['number_of_page_results']
        print(f"Fetched {len(issues)} / {total_results} issues...")
    return issues

def fetch_volume_details(api_key, volume_id):
    base_url = f'https://comicvine.gamespot.com/api/volume/4050-{volume_id}/'
    headers = {'User-Agent': 'PythonApp'}
    params = {
        'api_key': api_key,
        'format': 'json',
        'field_list': 'name,publisher'
    }
    response = make_request(base_url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()['results']

def fetch_issue_details(api_key, issue_id):
    base_url = f'https://comicvine.gamespot.com/api/issue/4000-{issue_id}/'
    headers = {'User-Agent': 'PythonApp'}
    params = {
        'api_key': api_key,
        'format': 'json',

    }
    response = make_request(base_url, headers=headers, params=params)
    response.raise_for_status()

    return response.json()['results']


def main(api_key, series_name_query):
    series_id = search_series(api_key, series_name_query)
    print(f"Found series ID: {series_id}")
    
    volume_details = fetch_volume_details(api_key, series_id)
    print(f"Volume details fetched for series ID: {series_id}")
    
    published_by = volume_details['publisher']['name'] if volume_details['publisher'] else 'N/A'
    issues_list = fetch_all_issues_for_series(api_key, series_id)

    with open('comic_series_info.csv', 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['Issue Name', 'Published By', 'Issue', 'Cover Date', 'In Store Date', 'Creators', 'Key Issue Notes']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for i, issue_summary in enumerate(issues_list, 1):
            try:
                issue_details = fetch_issue_details(api_key, issue_summary['id'])
                print(f"Fetching details for issue {i}/{len(issues_list)}: {issue_details.get('name')}")
                creators = '; '.join([f"{person['name']} - {person['role']}" for person in issue_details.get('person_credits', [])])
                key_issue_notes = issue_details.get('deck', 'N/A')
                writer.writerow({
                    'Issue Name': issue_details.get('name'),
                    'Published By': published_by,
                    'Issue': issue_details.get('issue_number'),
                    'Cover Date': issue_details.get('cover_date'),
                    'In Store Date': issue_details.get('store_date'),
                    'Creators': creators,
                    'Key Issue Notes': key_issue_notes
                })
                sleep(rate_limit_delay)  # Wait for 20 seconds before making the next request
            except requests.exceptions.HTTPError as e:
                if e.response.status_code in (420, 503):
                    print("Rate limit hit. Sleeping for an hour.")
                    sleep(3600)  # Sleep for 60 seconds if rate limit is hit
                else:
                    raise
    print("Data written to comic_series_info.csv successfully.")


if __name__ == '__main__':
    main(api_key, series_name_query)