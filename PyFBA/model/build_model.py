from __future__ import print_function, absolute_import, division
import sys
import os
import copy
import errno
import PyFBA
import libsbml as sbml


def roles_to_model(rolesFile, id, name, orgtype="gramnegative", verbose=False):
    """
    Read in the 'assigned_functions' file from RAST and create a model.

    :param rolesFile: File path to assigned functions RAST file
    :type rolesFile: str
    :param id: Model ID
    :type id: str
    :param name: Model name
    :type name: str
    :param orgtype: Organism type
    :type orgtype: str
    :param verbose: Verbose output
    :type verbose: bool
    :return: The generated model object
    :rtype: Model
    """

    # Load ModelSEED database
    compounds, reactions, enzymes = \
            PyFBA.parse.model_seed.compounds_reactions_enzymes(orgtype)

    # Read in assigned functions file to build set of roles
    assigned_functions = PyFBA.parse.read_assigned_functions(rolesFile)
    roles = set()
    for rs in assigned_functions.values():
        roles.update(rs)

    # Obtain reactions for each role
    # Key is role, value is set of reaction ids
    model_reactions = PyFBA.filters.roles_to_reactions(roles)

    # Create model object
    model = PyFBA.model.Model(id, name, orgtype)
    for role, rxnIDs in model_reactions.items():
        for rxnID in rxnIDs:
            if rxnID in reactions:
                model.add_reactions({reactions[rxnID]})
                model.add_roles({role: {rxnID}})
            elif verbose:
                print("Reaction ID '{}' for role '{}'".format(rxnID, role),
                      "is not in our reactions list. Skipped.",
                      file=sys.stderr)

    # Set biomass equation based on organism type
    biomass_eqn = PyFBA.metabolism.biomass_equation(orgtype)
    model.set_biomass_reaction(biomass_eqn)
    return model


def save_model(model, out_dir):
    """
    Save all model information in multiple files.
    This is meant to be temporary until SBML output is functional.

    :param model: Model to save
    :type model: Model
    :param out_dir: Directory to store files
    :type out_dir: str
    """
    import datetime
    dt = datetime.datetime.now()
    prefix = model.name
    # Check if directory exists using method from
    # http://stackoverflow.com/a/5032238
    try:
        os.makedirs(out_dir)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

    # Begin by storing basic info
    fname = prefix + ".info"
    with open(os.path.join(out_dir, fname), "w") as f:
        f.write("id\t" + model.id + "\n")
        f.write("name\t" + model.name + "\n")
        f.write("organism_type\t" + model.organism_type + "\n")
        f.write("created_on\t" + dt.isoformat())

    # Store roles -> reaction ID lists
    fname = prefix + ".roles"
    with open(os.path.join(out_dir, fname), "w") as f:
        for rl, rIDs in model.roles.items():
            f.write(rl + "\t" + ";".join(rIDs) + "\n")

    # Store reaction IDs
    fname = prefix + ".reactions"
    with open(os.path.join(out_dir, fname), "w") as f:
        f.write("\n".join(model.reactions.keys()) + "\n")

    # Store compound IDs
    fname = prefix + ".compounds"
    with open(os.path.join(out_dir, fname), "w") as f:
        f.write("\n".join([str(c) for c in model.compounds]) + "\n")

    # Store gap-filled media
    fname = prefix + ".gfmedia"
    with open(os.path.join(out_dir, fname), "w") as f:
        if len(model.gapfilled_media) > 0:
            f.write("\n".join(model.gapfilled_media) + "\n")

    # Store gap-filled reaction, gap-fill step, and media
    fname = prefix + ".gfreactions"
    with open(os.path.join(out_dir, fname), "w") as f:
        if len(model.gf_reactions) > 0:
            for rxn, gf_info in model.gf_reactions.items():
                f.write(rxn + "\t" + gf_info[0] + "\t" + gf_info[1] + "\n")


def load_model(in_dir, prefix):
    """
    Load all model information from multiple files generated by
    the "save_model()" function.
    This is meant to be temporary until SBML input is functional.

    :param in_dir: Directory of files
    :type in_dir: str
    :param prefix: Files prefix
    :type prefix: str
    :return: The generated model object
    :rtype: Model
    """

    # Load info
    id = name = orgtype = None
    fname = prefix + ".info"
    with open(os.path.join(in_dir, fname)) as f:
        for l in f:
            item, value = l.rstrip("\n").split("\t", 1)
            if item == "id":
                id = value
            elif item == "name":
                name = value
            elif item == "organism_type":
                orgtype = value
            elif item == "created_on":
                pass  # Only stored for reference purpose

    if not id or not name or not orgtype:
        sys.stderr.write("Could not extract info:\n")
        sys.stderr.write("id:" + id + "\n")
        sys.stderr.write("name:" + name + "\n")
        sys.stderr.write("orgtype:" + orgtype + "\n")
        return None

    # Load roles -> reaction ID lists
    fname = prefix + ".roles"
    mroles = {}
    with open(os.path.join(in_dir, fname)) as f:
        for l in f:
            role, rIDs = l.rstrip("\n").split("\t", 1)
            mroles[role] = rIDs.split(";")

    # Load ModelSEED database
    compounds, reactions, enzymes = \
            PyFBA.parse.model_seed.compounds_reactions_enzymes(orgtype)

    # Load reaction IDs
    fname = prefix + ".reactions"
    mreactions = set()
    with open(os.path.join(in_dir, fname)) as f:
        for l in f:
            rxn = l.rstrip("\n")
            try:
                mreactions.add(reactions[rxn])
            except KeyError:
                sys.stderr.write("Reaction " + rxn + " was not found in the database. Skipping.")

    # Load gap-filled media
    fname = prefix + ".gfmedia"
    gapfilled_media = set()
    with open(os.path.join(in_dir, fname)) as f:
        for l in f:
            gfmed = l.rstrip("\n")
            gapfilled_media.add(gfmed)

    # Load gap-filled reaction IDs
    fname = prefix + ".gfreactions"
    gf_reactions = {}
    with open(os.path.join(in_dir, fname)) as f:
        for l in f:
            rxn, method, media = l.rstrip("\n").split("\t")
            gf_reactions[rxn] = (method, media)
            reactions[rxn].is_gapfilled = True
            reactions[rxn].gapfill_method = method

    # Create model object
    model = PyFBA.model.Model(id, name, orgtype)
    model.roles = copy.deepcopy(mroles)
    model.gapfilled_media = copy.copy(gapfilled_media)
    model.gf_reactions = copy.deepcopy(gf_reactions)
    model.add_reactions(mreactions)
    biomass_eqn = PyFBA.metabolism.biomass_equation(orgtype)
    model.set_biomass_reaction(biomass_eqn)

    return model


def save_sbml(model, out_dir=".", file_name=None):
    """
    Save model in SBML format. Currently using:
    SBML Level 3 Version 1 Core (Release 2)

    Contents of SBML file are adapted from KBase

    Code has been adapted from:
    http://sbml.org/Software/libSBML/docs/python-api/libsbml-python-creating-model.html

    :param model: Model to save
    :type model: PyFBA.model.Model
    :param out_dir: Directory to store files
    :type out_dir: str
    :return: None
    """
    # CONSTANTS
    LOWER_BOUND = -1000.0
    UPPER_BOUND = 1000.0

    # Function adapted from sbml web page listed above
    def check(value, message):
        """
        If 'value' is None, prints an error message constructed using
        'message' and then exits with status code 1.  If 'value' is an integer,
        it assumes it is a libSBML return status code.  If the code value is
        LIBSBML_OPERATION_SUCCESS, returns without further action; if it is not,
        prints an error message constructed using 'message' along with text from
        libSBML explaining the meaning of the code, and exits with status code 1.
        """
        if value is None:
            raise SystemError("LibSBML returned a null value "
                              "trying to {}.".format(message))

        elif type(value) is int:
            if value != sbml.LIBSBML_OPERATION_SUCCESS:
                err_code = sbml.OperationReturnValue_toString(value).strip()
                err_msg = ("Error encountered trying to {}. LibSBML returned "
                           "error code {}: '{}'".format(message, value,
                                                        err_code))
                raise SystemError(err_msg)

    # Create the SBML document for saving
    try:
        sbml_doc = sbml.SBMLDocument(3, 1)
    except ValueError:
        raise SystemError("Could not create an SBMLDocument object")

    # Create an SBML model in the document and set global information
    sbml_model = sbml_doc.createModel()
    check(sbml_model, "create SBML Model object")
    check(sbml_model.setName(model.name), "set Model Name")
    check(sbml_model.setId(model.id), "set Model ID")

    # Create unit definitions
    # Flux rate contains 3 units
    flux_rate = sbml_model.createUnitDefinition()
    check(flux_rate, "create unit definition")
    check(flux_rate.setId("mmol_per_gDW_per_hr"), "set unit definition ID")
    # Mole unit
    unit = flux_rate.createUnit()
    check(unit, "create unit on mmol_per_gDW_per_hr")
    check(unit.setKind(sbml.UNIT_KIND_MOLE), "set unit mole")
    check(unit.setScale(-3), "set unit scale")
    # Gram unit
    unit = flux_rate.createUnit()
    check(unit, "create unit on mmol_per_gDW_per_hr")
    check(unit.setKind(sbml.UNIT_KIND_GRAM), "set unit gram")
    check(unit.setExponent(-1), "set unit exponent")
    # Second unit
    unit = flux_rate.createUnit()
    check(unit, "create unit on mmol_per_gDW_per_hr")
    check(unit.setKind(sbml.UNIT_KIND_SECOND), "set unit second")
    check(unit.setExponent(-1), "set unit exponent")
    check(unit.setMultiplier(1/3600), "set unit multiplier")

    # Create compartments
    # Two compartments: c0 and e0
    # c0
    comp = sbml_model.createCompartment()
    check(comp, "create compartment")
    check(comp.setId("c0"), "set compartment ID")
    check(comp.setName("c0"), "set compartment name")
    # e0
    comp = sbml_model.createCompartment()
    check(comp, "create compartment")
    check(comp.setId("e0"), "set compartment ID")
    check(comp.setName("e0"), "set compartment name")

    # Create compound species
    # Must iterate through all compounds in the model
    for c in model.compounds:
        curr_comp = c.location + "0"
        s = sbml_model.createSpecies()
        check(s, "create species")
        check(s.setId(c.model_seed_id + "_" + curr_comp), "set species ID")
        check(s.setName(c.name), "set species name")
        check(s.setCompartment(curr_comp), "set species compartment")
        # TODO: properly set charge
        # check(s.setCharge(0), "set species charge")
        # TODO: properly set boundary
        check(s.setBoundaryCondition(False), "set species boundary condition")

    # Create reactions
    # Must iterate through all reactions in the model
    for rid, r in model.reactions.items():
        curr_rxn = sbml_model.createReaction()
        check(curr_rxn, "create reaction")
        check(curr_rxn.setId(rid), "set reaction ID")
        check(curr_rxn.setName(r.name), "set reaction name")
        check(curr_rxn.setReversible(r.direction == "="),
              "set reaction reversibility")

        # Start with left side
        for c, c_abun in r.left_abundance.items():
            if r.direction == ">" or r.direction == "=":
                r_comp = curr_rxn.createReactant()
                check(r_comp, "create reactant")
            else:
                r_comp = curr_rxn.createProduct()
                check(r_comp, "create product")
            check(r_comp.setSpecies(c.model_seed_id + "_" + c.location + "0"),
                  "assign reaction species")
            check(r_comp.setStoichiometry(float(c_abun)),
                  "assign stoichiometry")
        # Next is right side
        for c, c_abun in r.right_abundance.items():
            if r.direction == ">" or r.direction == "=":
                r_comp = curr_rxn.createProduct()
                check(r_comp, "create product")
            else:
                r_comp = curr_rxn.createReactant()
                check(r_comp, "create reactant")
            check(r_comp.setSpecies(c.model_seed_id + "_" + c.location + "0"),
                  "assign reaction species")
            check(r_comp.setStoichiometry(float(c_abun)),
                  "assign stoichiometry")

        # Create kinetic law
        kinetic_law = curr_rxn.createKineticLaw()
        check(kinetic_law, "create kinetic law")
        param_name = "mmol_per_gDW_per_hr"
        # Create lower bound parameter
        lb_param = kinetic_law.createParameter()
        check(lb_param, "create lower bound parameter")
        check(lb_param.setId("LOWER_BOUND"), "set lower bound parameter ID")
        check(lb_param.setName(param_name), "set lower bound parameter name")
        check(lb_param.setValue(LOWER_BOUND),
              "set lower bound parameter value")
        # Create upper bound parameter
        ub_param = kinetic_law.createParameter()
        check(ub_param, "create upper bound parameter")
        check(ub_param.setId("UPPER_BOUND"), "set upper bound parameter ID")
        check(ub_param.setName(param_name), "set upper bound parameter name")
        check(ub_param.setValue(UPPER_BOUND),
              "set upper bound parameter value")
        # Create flux value parameter
        fv_param = kinetic_law.createParameter()
        check(fv_param, "create flux value parameter")
        check(fv_param.setId("FLUX_VALUE"), "set flux value parameter ID")
        check(fv_param.setName(param_name), "set flux value parameter name")
        check(fv_param.setValue(0.0), "set flux value parameter value")
        # Create objective coefficient parameter
        fv_param = kinetic_law.createParameter()
        check(fv_param, "create objective coefficient parameter")
        check(fv_param.setId("OBJECTIVE_COEFFICIENT"),
              "set objective coefficient parameter ID")
        check(fv_param.setValue(0.0),
              "set objective coefficient parameter value")
        # Set math
        math_xml = """<math xmlns=\"http://www.w3.org/1998/Math/MathML">
        <ci> FLUX_VALUE </ci>
        </math>"""
        math_ast = sbml.readMathMLFromString(math_xml)
        check(math_ast, "create MathML")
        check(kinetic_law.setMath(math_ast), "set math on kinetic law")

    # Create biomass reaction
    bio_rxn = sbml_model.createReaction()
    check(bio_rxn, "create biomass reaction")
    check(bio_rxn.setId("biomass"), "set biomass reaction ID")
    check(bio_rxn.setName("biomass"), "set biomass reaction name")
    check(bio_rxn.setReversible(False), "set biomass reaction reversibility")
    # Left compounds
    for c, c_abun in model.biomass_reaction.left_abundance.items():
        # Add compound if was not added previously
        if not model.has_compound(c):
            curr_comp = c.location + "0"
            s = sbml_model.createSpecies()
            check(s, "create species")
            check(s.setId(c.model_seed_id + "_" + curr_comp), "set species ID")
            check(s.setName(c.name), "set species name")
            check(s.setCompartment(curr_comp), "set species compartment")
            # TODO: properly set charge
            # check(s.setCharge(0), "set species charge")
            # TODO: properly set boundary
            check(s.setBoundaryCondition(False),
                  "set species boundary condition")

        r_comp = bio_rxn.createReactant()
        check(r_comp, "create reactant")
        check(r_comp.setSpecies(c.model_seed_id + "_" + c.location + "0"),
              "assign reaction species")
        check(r_comp.setStoichiometry(float(c_abun)),
              "assign stoichiometry")

    # Right compounds
    for c, c_abun in model.biomass_reaction.right_abundance.items():
        # Add compound if was not added previously
        if not model.has_compound(c):
            curr_comp = c.location + "0"
            s = sbml_model.createSpecies()
            check(s, "create species")
            check(s.setId(c.model_seed_id + "_" + curr_comp), "set species ID")
            check(s.setName(c.name), "set species name")
            check(s.setCompartment(curr_comp), "set species compartment")
            # TODO: properly set charge
            # check(s.setCharge(0), "set species charge")
            # TODO: properly set boundary
            check(s.setBoundaryCondition(False),
                  "set species boundary condition")

        r_comp = bio_rxn.createProduct()
        check(r_comp, "create product")
        check(r_comp.setSpecies(c.model_seed_id + "_" + c.location + "0"),
              "assign reaction species")
        check(r_comp.setStoichiometry(float(c_abun)),
              "assign stoichiometry")

    # Kinetic law
    kinetic_law = bio_rxn.createKineticLaw()
    check(kinetic_law, "create kinetic law")
    param_name = "mmol_per_gDW_per_hr"
    # Lower bound parameter
    lb_param = kinetic_law.createParameter()
    check(lb_param, "create lower bound parameter")
    check(lb_param.setId("LOWER_BOUND"), "set lower bound parameter ID")
    check(lb_param.setName(param_name), "set lower bound parameter name")
    check(lb_param.setValue(0.0), "set lower bound parameter value")
    # Upper bound parameter
    ub_param = kinetic_law.createParameter()
    check(ub_param, "create upper bound parameter")
    check(ub_param.setId("UPPER_BOUND"), "set upper bound parameter ID")
    check(ub_param.setName(param_name), "set upper bound parameter name")
    check(ub_param.setValue(UPPER_BOUND), "set upper bound parameter value")
    # Create flux value parameter
    fv_param = kinetic_law.createParameter()
    check(fv_param, "create flux value parameter")
    check(fv_param.setId("FLUX_VALUE"), "set flux value parameter ID")
    check(fv_param.setName(param_name), "set flux value parameter name")
    check(fv_param.setValue(0.0), "set flux value parameter value")
    # Create objective coefficient parameter
    fv_param = kinetic_law.createParameter()
    check(fv_param, "create objective coefficient parameter")
    check(fv_param.setId("OBJECTIVE_COEFFICIENT"),
          "set objective coefficient parameter ID")
    check(fv_param.setValue(1.0), "set objective coefficient parameter value")
    # Set math
    math_xml = """<math xmlns=\"http://www.w3.org/1998/Math/MathML">
    <ci> FLUX_VALUE </ci>
    </math>"""
    math_ast = sbml.readMathMLFromString(math_xml)
    check(math_ast, "create MathML")
    check(kinetic_law.setMath(math_ast), "set math on kinetic law")

    # Save as XML
    if file_name is None:
        save_as = os.path.join(out_dir, model.name + ".xml")
    else:
        save_as = os.path.join(out_dir, file_name)
    save = sbml.writeSBML(sbml_doc, save_as)
    if save != 1:
        print("Failed to save model as:", save_as, file=sys.stderr)
    else:
        print("Saved model successfully to file:", save_as, file=sys.stderr)
