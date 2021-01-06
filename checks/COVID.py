# vim:ts=8:sw=8:tw=0:noet

import re
import logging as log

from yapsy.IPlugin import IPlugin
from customwarnings import DataCheckWarningLevel,DataCheckWarning,DataCheckEntityType

covidNetworkName = 'bbmri-eric:networkID:EU_BBMRI-ERIC:networks:COVID19'
covidProspectiveCollectionIdPattern =  '.*:COVID19PROSPECTIVE$'

class COVID(IPlugin):
	def check(self, dir, args):
		warnings = []
		log.info("Running COVID content checks (COVID)")
		biobankHasCovidCollection = {}
		biobankHasCovidProspectiveCollection = {}
		biobankHasCovidControls = {}

		for collection in dir.getCollections():
			biobankId = dir.getCollectionBiobank(collection['id'])
			biobank = dir.getBiobankById(biobankId)
			biobank_capabilities = []
			if 'capabilities' in biobank:
				for c in biobank['capabilities']:
					biobank_capabilities.append(c['id'])
			biobank_covid = []
			if 'covid19biobank' in biobank:
				for c in biobank['covid19biobank']:
					biobank_covid.append(c['id'])
			biobank_networks = []
			if 'network' in biobank:
				for n in biobank['network']:
					biobank_networks.append(n['id'])

			OoM = collection['order_of_magnitude']['id']

			materials = []
			if 'materials' in collection:
				for m in collection['materials']:
					materials.append(m['id'])
			
			data_categories = []
			if 'data_categories' in collection:
				for c in collection['data_categories']:
					data_categories.append(c['id'])

			types = []
			if 'type' in collection:
				for t in collection['type']:
					types.append(t['id'])
                        
			diags = []
			diag_ranges = []
			covid_diag = False
			covid_control = False

			for d in collection['diagnosis_available']:
				if re.search('-', d['id']):
					diag_ranges.append(d['id'])
				else:
					diags.append(d['id'])

			for d in diags+diag_ranges:
				# ICD-10
				if re.search('U07', d):
					covid_diag = True
				# ICD-10
				if re.search('Z03.818', d):
					covid_control = True
				# ICD-11
				if re.search('RA01', d):
					covid_diag = True
				# SNOMED CT
				if re.search('(840533007|840534001|840535000|840536004|840539006|840544004|840546002)', d):
					covid_diag = True

                        
			if covid_diag:
				biobankHasCovidCollection[biobank['id']] = True
			else:
				# just initialize the record if not yet set at all - otherwise don't touch!
				if not biobank['id'] in biobankHasCovidCollection:
					biobankHasCovidCollection[biobank['id']] = False

			if covid_control:
				biobankHasCovidControls[biobank['id']] = True
			else:
				# just initialize the record if not yet set at all - otherwise don't touch!
				if not biobank['id'] in biobankHasCovidControls:
					biobankHasCovidControls[biobank['id']] = False

			if (covid_diag or covid_control) and diag_ranges:
				warning = DataCheckWarning(self.__class__.__name__, "", dir.getCollectionNN(collection['id']), DataCheckWarningLevel.ERROR, collection['id'], DataCheckEntityType.COLLECTION, "It seems that diagnoses contains range - this will render the diagnosis search ineffective for the given collection. Violating diagnosis term(s): " + '; '.join(diag_ranges))
				warnings.append(warning)

			if covid_diag or covid_control:
				if not covidNetworkName in biobank_networks:
					warning = DataCheckWarning(self.__class__.__name__, "", dir.getCollectionNN(collection['id']), DataCheckWarningLevel.ERROR, biobank['id'], DataCheckEntityType.BIOBANK, "Biobank contains COVID collection " + collection['id'] + ' but not marked as part of ' + covidNetworkName)
					warnings.append(warning)
				if not 'covid19' in biobank_covid:
					warning = DataCheckWarning(self.__class__.__name__, "", dir.getCollectionNN(collection['id']), DataCheckWarningLevel.ERROR, biobank['id'], DataCheckEntityType.BIOBANK, "Biobank contains COVID collection " + collection['id'] + ' but does not have "covid19" attribute in "covid19biobank" section of attributes')
					warnings.append(warning)


			if len(types) < 1:
				warning = DataCheckWarning(self.__class__.__name__, "", dir.getCollectionNN(collection['id']), DataCheckWarningLevel.ERROR, collection['id'], DataCheckEntityType.COLLECTION, "Collection type not provided")
				warnings.append(warning)
                        

			if re.search(covidProspectiveCollectionIdPattern, collection['id']):
				biobankHasCovidProspectiveCollection[biobank['id']] = True
				if not 'DISEASE_SPECIFIC' in types:
					warning = DataCheckWarning(self.__class__.__name__, "", dir.getCollectionNN(collection['id']), DataCheckWarningLevel.ERROR, collection['id'], DataCheckEntityType.COLLECTION, "Prospective COVID-19 collections must have DISEASE_SPECIFIC as one of its types")
					warnings.append(warning)
				if not 'PROSPECTIVE_COLLECTION' in types:
					warning = DataCheckWarning(self.__class__.__name__, "", dir.getCollectionNN(collection['id']), DataCheckWarningLevel.ERROR, collection['id'], DataCheckEntityType.COLLECTION, "Prospective COVID-19 collections must have PROSPECTIVE_COLLECTION as one of its types")
					warnings.append(warning)
				if not 'ProspectiveCollections' in biobank_covid:
					warning = DataCheckWarning(self.__class__.__name__, "", dir.getCollectionNN(collection['id']), DataCheckWarningLevel.ERROR, collection['id'], DataCheckEntityType.COLLECTION, "ProspectiveCollections capability must be specified in covid19biobank section of biobank attributes if there is a COVID19PROSPECTIVE collection provided")
					warnings.append(warning)
				if OoM > 0:
					warning = DataCheckWarning(self.__class__.__name__, "", dir.getCollectionNN(collection['id']), DataCheckWarningLevel.WARNING, collection['id'], DataCheckEntityType.COLLECTION, "Prospective collection type represents capability of setting up prospective collections - hence it should have zero order of magnitude")
					warnings.append(warning)
				if not covid_diag and not covid_control:
					warning = DataCheckWarning(self.__class__.__name__, "", dir.getCollectionNN(collection['id']), DataCheckWarningLevel.ERROR, collection['id'], DataCheckEntityType.COLLECTION, "COVID19PROSPECTIVE collection misses COVID-19 diagnosis or COVID-19 controls filled in")
					warnings.append(warning)

			if re.search('^Ability to collect', collection['name']) and (covid_diag or covid_control):
				if not re.search(covidProspectiveCollectionIdPattern, collection['id']):
					warning = DataCheckWarning(self.__class__.__name__, "", dir.getCollectionNN(collection['id']), DataCheckWarningLevel.ERROR, collection['id'], DataCheckEntityType.COLLECTION, 'Collection having "ability to collect" does not have COVID19PROSPECTIVE label')
					warnings.append(warning)
					# only report the following if it hasn't been reported above (hence only if the COVID19PROSPECTIVE does not match)
					if OoM > 0:
						warning = DataCheckWarning(self.__class__.__name__, "", dir.getCollectionNN(collection['id']), DataCheckWarningLevel.WARNING, collection['id'], DataCheckEntityType.COLLECTION, "Prospective collection type represents capability of setting up prospective collections - hence it should have zero order of magnitude")
						warnings.append(warning)


			if re.search('.*:COVID19$', collection['id']):
				if not 'DISEASE_SPECIFIC' in types:
					warning = DataCheckWarning(self.__class__.__name__, "", dir.getCollectionNN(collection['id']), DataCheckWarningLevel.ERROR, collection['id'], DataCheckEntityType.COLLECTION, "Existing COVID-19 collections must have DISEASE_SPECIFIC as one of its types")
					warnings.append(warning)
				if not 'DNA' in materials and not 'PATHOGEN' in materials and not 'PERIPHERAL_BLOOD_CELLS' in materials and not 'PLASMA' in materials and not 'RNA' in materials and not 'SALIVA' in materials and not 'SERUM' in materials and not 'WHOLE_BLOOD' in materials and not 'FECES' in materials and not 'BUFFY_COAT' in materials and not 'NASAL_SWAB' in materials and not 'THROAT_SWAB' in materials:
					warning = DataCheckWarning(self.__class__.__name__, "", dir.getCollectionNN(collection['id']), DataCheckWarningLevel.WARNING, collection['id'], DataCheckEntityType.COLLECTION, "Supect material types: existing COVID-19 collection does not have any of the common material types: DNA, PATHOGEN, PERIPHERAL_BLOOD_CELLS, PLASMA, RNA, SALIVA, SERUM, WHOLE_BLOOD, FECES, BUFFY_COAT, NASAL_SWAB, THROAT_SWAB")
					warnings.append(warning)
				if 'NASAL_SWAB' in materials or 'THROAT_SWAB' in materials or 'FECES' in materials and not ('BSL2' in biobank_covid or 'BSL3' in biobank_covid):
					warning = DataCheckWarning(self.__class__.__name__, "", dir.getCollectionNN(collection['id']), DataCheckWarningLevel.WARNING, collection['id'], DataCheckEntityType.COLLECTION, "Suspect situation: collection contains infectious material (nasal/throat swabs, faeces) while the parent biobank does not indicate BSL2 nor BSL3 available")
					warnings.append(warning)
				if not covid_diag:
					warning = DataCheckWarning(self.__class__.__name__, "", dir.getCollectionNN(collection['id']), DataCheckWarningLevel.ERROR, collection['id'], DataCheckEntityType.COLLECTION, "COVID19 collection misses COVID-19 diagnosis filled in")
					warnings.append(warning)


		for biobank in dir.getBiobanks():
			biobank_capabilities = []
			if 'capabilities' in biobank:
				for c in biobank['capabilities']:
					biobank_capabilities.append(c['id'])
			biobank_covid = []
			if 'covid19biobank' in biobank:
				for c in biobank['covid19biobank']:
					biobank_covid.append(c['id'])
			biobank_networks = []
			if 'network' in biobank:
				for n in biobank['network']:
					biobank_networks.append(n['id'])

			if covidNetworkName in biobank_networks and not 'covid19' in biobank_covid:
				warning = DataCheckWarning(self.__class__.__name__, "", dir.getBiobankNN(biobank['id']), DataCheckWarningLevel.ERROR, biobank['id'], DataCheckEntityType.BIOBANK, "Biobank is part of " + covidNetworkName + " but does not have covid19 among covid19biobank attributes")
				warnings.append(warning)
			if 'covid19' in biobank_covid and not covidNetworkName in biobank_networks:
				warning = DataCheckWarning(self.__class__.__name__, "", dir.getBiobankNN(biobank['id']), DataCheckWarningLevel.ERROR, biobank['id'], DataCheckEntityType.BIOBANK, "Biobank has covid19 among covid19biobank attributes but is not part of " + covidNetworkName)
				warnings.append(warning)

			# This is a simple check if the biobank has other services than just the attribute of being a covid19 biobank
			other_covid_services = False
			for s in biobank_covid:
				if s != 'covid19':
					other_covid_services = True

			if 'covid19' in biobank_covid and not (biobank['id'] in biobankHasCovidCollection or biobank['id'] in biobankHasCovidControls or other_covid_services):
				warning = DataCheckWarning(self.__class__.__name__, "", dir.getBiobankNN(biobank['id']), DataCheckWarningLevel.ERROR, biobank['id'], DataCheckEntityType.BIOBANK, "Biobank has covid19 among covid19biobank but has no relevant services nor any collection of COVID-19 samples nor any collection of COVID-19 controls")
				warnings.append(warning)
	
			if 'ProspectiveCollections' in biobank_covid and not biobank['id'] in biobankHasCovidProspectiveCollection:
				warning = DataCheckWarning(self.__class__.__name__, "", dir.getBiobankNN(biobank['id']), DataCheckWarningLevel.WARNING, biobank['id'], DataCheckEntityType.BIOBANK, "Biobank has ProspectiveCollections among covid19biobank attributes but has no prospective collection defined (collection ID matching '" + covidProspectiveCollectionIdPattern + "' regex pattern)")
				warnings.append(warning)

			if biobank['id'] in biobankHasCovidProspectiveCollection and not 'ProspectiveCollections' in biobank_covid:
				warning = DataCheckWarning(self.__class__.__name__, "", dir.getBiobankNN(biobank['id']), DataCheckWarningLevel.ERROR, biobank['id'], DataCheckEntityType.BIOBANK, "Biobank has prospective collection defined (collection ID matching '" + covidProspectiveCollectionIdPattern + "' regex pattern) but ProspectiveCollections is not among covid19biobank attributes")
				warnings.append(warning)

		return warnings
