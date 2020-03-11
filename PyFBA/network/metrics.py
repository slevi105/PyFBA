from __future__ import print_function, absolute_import, division
from .network import Network
import networkx as nx
import sys


def number_connected_components(network):
    """
    Count number of connected components in a network

    :param network: Network of nodes
    :type network: PyFBA.network.Network
    :return: Number of connected components
    :rtype: int
    """
    # Check type
    if not isinstance(network, Network):
        raise TypeError

    # Convert directed graph to undirected
    if network.graph.is_directed():
        return nx.number_connected_components(network.graph.to_undirected())

    return nx.number_connected_components(network.graph)


def clustering_coeff(network):
    """
    Calculate the clustering coefficient using the NetworkX library.

    :param network: Network of nodes
    :type network: PyFBA.network.Network
    :return: Clustering coefficient for nodes in the network
    :rtype: dict
    """
    # Check type
    if not isinstance(network, Network):
        raise TypeError

    # Check if network is empty
    if len(network.graph) == 0:
        raise ValueError("Network is empty")

    # Convert directed graph to undirected
    if network.graph.is_directed():
        return nx.clustering(network.graph.to_undirected())

    return nx.clustering(network.graph)


def avg_clustering_coeff(network):
    """
    Calculate the average clustering coefficient using the NetworkX library.

    :param network: Network of nodes and edges
    :type network: PyFBA.network.Network
    :return: Average clustering coefficient for all nodes in the network
    :rtype: float
    """
    # Check type
    if not isinstance(network, Network):
        raise TypeError

    # Check if network is empty
    if len(network.graph) == 0:
        raise ValueError("Network is empty")

    # Convert directed graph to undirected
    if network.graph.is_directed():
        return nx.average_clustering(network.graph.to_undirected())

    return nx.average_clustering(network.graph)


def closeness_centrality(network):
    """
    Calculate the closeness centrality using the NetworkX library.

    :param network: Network of nodes and edges
    :type network: PyFBA.network.Network
    :return: Closeness centrality for nodes in the network
    :rtype: dict
    """
    # Check type
    if not isinstance(network, Network):
        raise TypeError

    # Check if network is empty
    if len(network.graph) == 0:
        raise ValueError("Network is empty")

    return nx.closeness_centrality(network.graph)


def avg_closeness_centrality(network):
    """
    Calculate the average closeness centrality using the NetworkX library.

    :param network: Network of nodes and edges
    :type network: PyFBA.network.Network
    :return: Average closeness centrality for all nodes in the network
    :rtype: float
    """
    cc = closeness_centrality(network)
    return sum(list(cc.values())) / len(cc)


def betweenness_centrality(network):
    """
    Calculate the betweenness centrality using the NetworkX library.

    :param network: Network of nodes and edges
    :type network: PyFBA.network.Network
    :return: Betweenness centrality for nodes in the network
    :rtype: dict
    """
    # Check type
    if not isinstance(network, Network):
        raise TypeError

    # Check if network is empty
    if len(network.graph) == 0:
        raise ValueError("Network is empty")

    return nx.betweenness_centrality(network.graph)


def avg_betweenness_centrality(network):
    """
    Calculate the average betweenness centrality using the NetworkX library.

    :param network: Network of nodes and edges
    :type network: PyFBA.network.Network
    :return: Average betweenness centrality for all nodes in the network
    :rtype: float
    """
    bc = betweenness_centrality(network)
    return sum(list(bc.values())) / len(bc)


def diameter(network):
    """
    Calculate the diameter of the network (the longest path between two nodes).

    :param network: Network of nodes and edges
    :type network: PyFBA.network.Network
    :return: Network diameter
    :rtype: int
    """
    # Check type
    if not isinstance(network, Network):
        raise TypeError

    # Check if network is empty
    if len(network.graph) == 0:
        raise ValueError("Network is empty")

    undir_network = network.graph.to_undirected()

    # Check if network is connected
    if nx.is_connected(undir_network):
        return nx.diameter(undir_network)

    print("Warning: network is not fully connected. Will calculate largest",
          "diameter", file=sys.stderr)

    # Network is not connected -- find diameter for each component
    largest_diam = 0
    for c in nx.connected_component_subgraphs(undir_network):
        curr_diam = nx.diameter(c)

        # Store largest diameter
        if curr_diam > largest_diam:
            largest_diam = curr_diam

    return largest_diam


def jaccard_distance(net1, net2, verbose=False):
    """
    Calculate the Jaccard distance between two networks. Here, the Jaccard
    distance between two networks is defined as one minus the quotient of the
    intersection of edges and the union of edges:

                J(net1, net2) = 1 - (I(net1, net2) / U(net1, net2))

    Note: Jaccard distance is a metric defined for sets. Here the sets are
    the edges in each network

    :param net1: First network to use in comparison
    :type net1: PyFBA.network.Network
    :param net2: Second network to use in comparison
    :type net2: PyFBA.network.Network
    :return: Jaccard distance
    :rtype: float
    """
    # Check types
    if not isinstance(net1, Network):
        raise TypeError("First network is not a Network object")
    elif not isinstance(net2, Network):
        raise TypeError("Second network is not a Network object")

    union = network_union(net1, net2).get_nx_graph()

    # Calculate intersection by removing nodes not present in both
    # Removing nodes result in removing edges connected to it
    g1 = net1.get_nx_graph()
    g2 = net2.get_nx_graph()
    intersection = g1.copy()
    intersection.remove_nodes_from(n for n in g1 if n not in g2)

    return 1 - (intersection.number_of_edges() / union.number_of_edges())


def network_union(net1, net2):
    """

    Create a new network with the combined edges between two networks

    :param net1: Network 1
    :type net1: PyFBA.network.Network
    :param net2: Network 2
    :type net2: PyFBA.network.Network
    :return: Network union
    :rtype: PyFBA.network.Network
    """
    union = net1.get_nx_graph().copy()
    # Set data to True so reaction information gets passed through
    for e in net2.edges_iter(data=True):
        if not union.has_edge(e[0], e[1]):
            union.add_edge(*e)
    return Network(graph=union)


def core_network(net1, net2):
    """
    Core network is defined by the shared edges of two networks

    :param net1: Network 1
    :type net1: PyFBA.network.Network
    :param net2: Network 2
    :type net2: PyFBA.network.Network
    :return: Core network
    :rtype: PyFBA.network.Network
    """
    ng1 = net1.get_nx_graph()
    ng2 = net2.get_nx_graph()
    new_graph = ng1.copy()
    new_graph.remove_nodes_from(node for node in ng1 if node not in ng2)
    return Network(graph=new_graph)