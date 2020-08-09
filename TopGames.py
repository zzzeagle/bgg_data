import requests
import csv
import os
from lxml import html
import xml.etree.ElementTree as ET


def get_top_games(pages):
    i: int = 1
    results = []
    while i < pages:
        # Get the list of top games from BGG
        page = requests.get('https://boardgamegeek.com/browse/boardgame/page/' + str(i))
        tree = html.fromstring(page.content)
        # Select the item URL which includes the item ID
        games = tree.xpath('//*[contains(@class,"collection_objectname")]//a/@href')
        results = results + games
        i = i + 1
    ids = list(map(lambda x: x.split('/')[2], results))
    return ids


def load_game_stats(ids):
    game_ids = ','.join(ids)
    data = requests.get('https://api.geekdo.com/xmlapi2/thing?type=boardgame&stats=1&id=' + game_ids)

    with open('game_data.xml', 'wb') as f:
        f.write(data.content)


def parse_xml(xmlfile):
    tree = ET.parse(xmlfile)

    root = tree.getroot()

    games = []

    for item in root.findall("./item"):
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
            get_links(item, link)

        get_ranks(item)

    return games


def get_links(item, linktype):
    links = []
    for link in item.findall("./link/[@type='" + linktype + "']"):
        link_item = {}
        link_item['gameId'] = item.attrib['id']
        link_item['id'] = link.attrib['id']
        link_item['value'] = link.attrib['value']
        links.append(link_item)

    # Check to see if there are any links, otherwise we would error.
    if links:
        append_to_csv(links, linktype + '.csv')


def get_ranks(item):
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
            append_to_csv(rank_data, rank_type + ".csv")


def append_to_csv(games, filename):
    # Make output folder if it doesn't exist
    if not os.path.exists('output'):
        os.makedirs('output')

    file_location = 'output/' + filename

    # Check if the file exists, so we know if we need to write headers later
    file_exists = os.path.isfile(file_location)

    with open(file_location, 'a', newline='', encoding="utf-8") as csvfile:
        fields = games[0].keys()

        writer = csv.DictWriter(csvfile, fieldnames=fields)

        # If this is a new file, write the headers
        if not file_exists:
            writer.writeheader()

        writer.writerows(games)


def bgg_api_calls(ids):
    length = len(ids)
    i = 0
    while i < length:
        load_game_stats(ids[i:i + 400])
        game_data = parse_xml('game_data.xml')
        append_to_csv(game_data, 'game_data.csv')
        i = i + 400


def main():
    # Scrape BGG browse page to top n*100 games by rank
    top_games = get_top_games(10)

    # Get number of games
    number_of_games = len(top_games)

    i = 0
    while i < number_of_games:
        load_game_stats(top_games[i:i + 400])
        game_data = parse_xml('game_data.xml')
        append_to_csv(game_data, 'game_data.csv')
        i = i + 400

    # Take the IDs from the web scraping and use the API to create CSVs
    #bgg_api_calls(top_games)


if __name__ == "__main__":
    main()
