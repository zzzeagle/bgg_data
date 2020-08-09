import requests
import csv
import os
from lxml import html
import xml.etree.ElementTree as ET
import matplotlib.pyplot as plt
import seaborn as sns


def browse_bgg(url, xpath, pages):
    """Return a list of BGG ids for the top n pages"""
    i: int = 1
    results = []

    # If pages = 0, then get all pages for the URL
    if pages == 0:
        page = requests.get(str(url) + str(i))
        tree = html.fromstring(page.content)
        # Find the last page number on the first page
        pages = int(tree.xpath('//*[@title="last page"]/text()')[1][1:-1])

    while i < pages:
        # Get the list of top games from BGG
        page = requests.get(str(url) + str(i))
        tree = html.fromstring(page.content)
        # Select the item URL which includes the item ID
        games = tree.xpath(xpath)
        results = results + games
        i = i + 1
    # The url selected is /boardgame/ID/name. Select just the ID.
    ids = list(map(lambda x: x.split('/')[2], results))
    return ids


def call_bgg_api(api, ids):
    """Use the BGG API to get an XML file with the data for games with the IDs"""
    game_ids = ','.join(ids)
    data = requests.get(api + game_ids)

    with open('game_data.xml', 'wb') as f:
        f.write(data.content)


def parse_xml(xml_file):
    """Parse the XML file returned by the BGG API"""
    tree = ET.parse(xml_file)

    root = tree.getroot()

    return root


def process_game_data(item):
    """Process the data from the XML file that has a one-to-one relationship with the board game"""
    games = []
    game = {}
    game['id'] = item.attrib['id']
    game['name'] = item.findall("./name/[@type='primary']")[0].attrib['value']
    attributes = ['./minplayers',
                  './maxplayers',
                  './playingtime',
                  './minplaytime',
                  './maxplaytime',
                  './minage',
                  './statistics/ratings/usersrated',
                  './statistics/ratings/average',
                  './statistics/ratings/bayesaverage',
                  './statistics/ratings/stddev',
                  './statistics/ratings/median',
                  './statistics/ratings/owned',
                  './statistics/ratings/trading',
                  './statistics/ratings/wanting',
                  './statistics/ratings/wishing',
                  './statistics/ratings/numcomments',
                  './statistics/ratings/numweights',
                  './statistics/ratings/averageweight',
                  './yearpublished']
    for att in attributes:
        game[att] = item.find(att).attrib['value']

    games.append(game)
    append_to_csv(games, '', 'game_data.csv')


def process_link_data(game):
    """Each game has a number of relationships to other data (designer, categories, artists, etc...
    These links are one-to-many. For each link type create a csv with the data."""
    # Link items to select. Each game may have more than one item for each of these links.
    # So for each link a CSV is created with that data.
    links = ['boardgamecategory',
             'boardgamemechanic',
             'boardgamefamily',
             'boardgameimplementation',
             'boardgamedesigner',
             'boardgameartist',
             'boardgamepublisher']
    for link in links:
        get_links(game, link)


def get_links(item, link_type):
    """Get each link of the link type and save to a CSV file"""
    links = []
    for link in item.findall("./link/[@type='" + link_type + "']"):
        link_item = {}
        link_item['gameId'] = item.attrib['id']
        link_item['id'] = link.attrib['id']
        link_item['value'] = link.attrib['value']
        links.append(link_item)

    # Check to see if there are any links, otherwise we would error.
    if links:
        append_to_csv(links, 'links', link_type + '.csv')


def process_rank_data(item):
    """Process the rank data for a game
        A game an have more than one ranking
        Make a new file for each rank type"""
    ranks = item.findall('./statistics/ratings/ranks/rank')
    game_id = item.attrib['id']
    if ranks:
        for rank in ranks:
            rank_data = []
            rank_info = {}
            rank_type = rank.attrib['name']
            rank_info['gameid'] = game_id
            rank_info['value'] = rank.attrib['value']
            rank_info['bayesaverage'] = rank.attrib['bayesaverage']
            rank_data.append(rank_info)
            append_to_csv(rank_data, 'ranks', rank_type + ".csv")


def append_to_csv(games, folder, filename):
    """Function to add data to a CSV
        Creates the file if it doesn't exist"""
    # Make output folder if it doesn't exist
    if not os.path.exists('output'):
        os.makedirs('output')
    path = os.path.join('output', folder)
    if not os.path.exists(path):
        os.makedirs(path)

    file_location = os.path.join(path, filename)

    # Check if the file exists, so we know if we need to write headers later
    file_exists = os.path.isfile(file_location)

    with open(file_location, 'a', newline='', encoding="utf-8") as csvfile:
        fields = games[0].keys()

        writer = csv.DictWriter(csvfile, fieldnames=fields)

        # If this is a new file, write the headers
        if not file_exists:
            writer.writeheader()

        writer.writerows(games)


def process_family(item, family_id):
    links = []

    family_name = item.findall("./name/[@type='primary']")[0].attrib['value']
    for link in item.findall("./link"):
        game_link = {}
        game_link['family_id'] = family_id
        game_link['family_name'] = family_name
        game_link['game_id'] = link.attrib['id']
        game_link['name'] = link.attrib['value']
        links.append(game_link)
    append_to_csv(links, 'family', 'families.csv')


def main():
    # Scrape BGG browse page to top n*100 games by rank
    top_games = browse_bgg('https://boardgamegeek.com/browse/boardgame/page/', '//*[contains(@class,"collection_objectname")]//a/@href', 2)

    # Get number of games
    number_of_games = len(top_games)

    i = 0
    while i < number_of_games:
        call_bgg_api('https://api.geekdo.com/xmlapi2/thing?type=boardgame&stats=1&id=', top_games[i:i + 400])
        game_data = parse_xml('game_data.xml')
        for game in game_data.findall("./item"):
            process_game_data(game)
            process_rank_data(game)
            process_link_data(game)
        i = i + 400

    # Scrape the board game families pages to get a list of boardgame family ids
    families = browse_bgg('https://boardgamegeek.com/browse/boardgamefamily/page/',  '//*[contains(@class,"forum_table")]//a/@href', 2)
    number_of_families = len(families)

    k = 0
    while k < number_of_families:
        call_bgg_api('https://api.geekdo.com/xmlapi2/family?type=boardgamefamily&id=', families[k:k+400])
        family_data = parse_xml('game_data.xml')
        for family in family_data.findall("./item"):
            family_id = family.attrib['id']
            process_family(family, family_id)
        k = k + 400



if __name__ == "__main__":
    main()
