
import json
import numpy as np
from torch_geometric.datasets import Planetoid


def run_zuordnung(getml_word_data):
    """
    The matching process is based on the word matrix of the abstracts' content. That data is stored differently in the data of Izadi et al's GNN paper (hereinafter referred to as GNN paper or GNN data) and getML's data source. In the GNN's case, words are stored one-hot-encoded in a matrix (e.g. [0,0,1,0,1]), while getML data source simply lists the words and their associated index in the on-hot-encoded word matrix (e.g.: [word2, word4]). The following routine first retrieves the index of the GNN matrix. Due to different offsets, the word indices between both data source do not align. Therefore, we compute the difference between adjacent word indices and compare them across sources. If the patterns match, we have found a match between both sources and save their associated dataframe indices.

    It turns out there is a perfect match between both sources and every observation in one source finds its counterpart in the other source.
    """

    getml_word_data = getml_word_data.to_pandas()

    gnn_word_data = Planetoid(name="Cora", root="")

    zuordnung = []
    for getml_idx in getml_word_data["paper_id"].unique():
        getml_positions = [
            int(ele[4:])
            for ele in getml_word_data[getml_word_data["paper_id"] == getml_idx][
                "word_cited_id"
            ].values
        ]
        getml_positions = np.sort(getml_positions)

        getml_words_pattern = [
            j - i for i, j in zip(getml_positions[:-1], getml_positions[1:])
        ]

        for gnn_idx in range(len(gnn_word_data[0].x)):
            gnn_positions = [
                i
                for i, x in enumerate(
                    [int(x) for x in list(gnn_word_data[0].x[gnn_idx])]
                )
                if x == 1
            ]
            gnn_words_pattern = [
                j - i for i, j in zip(gnn_positions[:-1], gnn_positions[1:])
            ]

            if gnn_words_pattern == getml_words_pattern:
                match = (int(getml_idx), gnn_idx)
                zuordnung.append(match)
                break


    with open('assets/zuordnung.json', 'w') as file:
        print("Writing to file")
        json.dump(zuordnung, file)
        print('Done')

    print(zuordnung)

