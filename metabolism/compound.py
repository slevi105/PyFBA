"""
A compound is the essential metabolic compound that is involved in a
reaction.

"""

COMMON_REACTION_LIMIT = 5


class Compound:
    """
    A compound has at the very minimum a name and a location. We
    provide a mechanism for you to add other information to the compound
    in case you need it:

        name:       the name of the  compound
        location:   the location of the compound. e.g.:
                        e: extracellular
                        c: cytoplasmic
                        h: chloroplast
                        p: periplasm
        reactions:  a set of reaction objects that this compound is
                    connected to
        model_seed_id:  the cpd id from the model seed.
        abbreviation:   a short name for the compound
        formula:        the compounds formula
        mw:             the molecular weight of the compound
        common:         Boolean: this is a common compound. I roughly
                        define this as being in > COMMON_REACTION_LIMIT
                        reactions. See my NOTES.md for a graph on this.
        charge:         the charge associated with the compound
        uptake_secretion: imported from the SBML file (boolean)

    """

    def __init__(self, name, location):
        self.name = name
        self.location = location
        self.reactions = set()
        self.model_seed_id = name
        self.abbreviation = None
        self.formula = None
        self.mw = 0
        self.common = False
        self.charge = 0
        self.uptake_secretion = False

    def __eq__(self, other):
        """Two compounds are equal if they have the same name and the
        same location"""
        if isinstance(other, Compound):
            return (self.name, self.location) == (other.name, other.location)
        else:
            return NotImplemented
    
    def __cmp__(self, other):
        """Compare whether two things are the same"""
        if isinstance(other, Compound):
            if __eq__(other):
                return 0
            else:
                return 1
        else:
            return NotImplemented

    def __ne__(self, other):
        """Are these not equal?"""
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    def __hash__(self):
        """The hash function is based on the name of the compound"""
        return hash((self.name, self.location))

    def __str__(self):
        """The to string function"""
        return self.name + " (location: " + self.location + ")"


    def add_reactions(self, rxns):
        """
        Add a reaction that this compound is involved in. You  can add a set of reactions. See the note above about the
        number of reactions.

        :param rxns: A set of reactions
        :type rxns: set
        """
        if isinstance(rxns, set):
            self.reactions.update(rxns)
        else:
            raise TypeError(
                "You need to add a set of reactions to a compound"
            )


    def has_reaction(self, rxn):
        """
        Is this compound involved in this reaction?
        :param rxn: A metabolism.Reaction object
        :type rxn: metabolism.Reaction
        """
        return rxn in self.reactions


    def number_of_reactions(self):
        """How many reactions is this compound involved in?"""
        return len(self.reactions)


    def all_reactions(self):
        """Return a set of all the reactions that this compound
        is involved in"""
        return self.reactions


    def is_common(self, rct_limit=COMMON_REACTION_LIMIT):
        """
        Is this a common compound? This requires that you have
        added reactions to this compound.
        
        You can either specify the number of reactions or use our
        default that is currently 50.

        :param rct_limit: The limit for a compound to be considered common
        :type rct_limit: int
        """
        if self.number_of_reactions() > rct_limit:
            self.common = True
        else:
            self.common = False
        return self.common
