
#%%
import pandas as pd 
import re
from functools import reduce
import copy

log_path = './neo4j-mdr-db/neo4j/logs'

#%%
filenames = [
    f'{log_path}/query.log',
    f'{log_path}/query.log.1',
    f'{log_path}/query.log.2',
    f'{log_path}/query.log.3',
    f'{log_path}/query.log.4',
    f'{log_path}/query.log.5',
    f'{log_path}/query.log.6',
    f'{log_path}/query.log.7',
    f'{log_path}/query.log.8',
    f'{log_path}/query.log.9',
    f'{log_path}/query.log.10',
    f'{log_path}/query.log.11',
    f'{log_path}/query.log.12',
    f'{log_path}/query.log.13',
    f'{log_path}/query.log.14',
    f'{log_path}/query.log.15',
    f'{log_path}/query.log.16',
    f'{log_path}/query.log.17',
    f'{log_path}/query.log.18',
]
with open(f'{log_path}/query_copy.log', 'w') as outfile:
    for fname in filenames:
        with open(fname) as infile:
            for line in infile:
                outfile.write(line)

# %%
with (open(f'{log_path}/query_copy.log',encoding='ISO-8859-1') ) as f:
    #take the corpus of the file
    corpus = f.read()
# %%
sub_corpus = re.sub(r'\n', ' ', corpus)
# sub_corpus = re.sub(r'\\n', ' ', sub_corpus)
#%%

each_info = sub_corpus.split('+0000 INFO')

#%%
len(each_info)
#%%
wh_query_list = list(filter (lambda x: 'WHERE' in x, each_info))
print(len(wh_query_list))
print(wh_query_list[-5:])
#%%
log_list = []
for i_th in wh_query_list:
    # i_th = wh_query_list[-2]
    # print (i_th)
    lines = re.sub(r'MATCH', r'\nMATCH ', i_th) 
    lines = re.sub(r'RETURN', r'\nRETURN ', lines)
    lines = re.sub(r'WITH', r'\nWITH ', lines)
    lines = re.sub(r'WHERE', r'\nWHERE ', lines) 
    qry = {}
    qry.update(dict(
            [('match', list(filter (lambda x: 'MATCH' in x, lines.split('\n'))) )]
        )
    )
    qry.update(dict(
            [('where', list(filter (lambda x: 'WHERE' in x, lines.split('\n'))) )]
        )
    )
    try:
        if qry['match'] !=[]:
            # print(f"match treatment:")
            # print (qry['match'])
            e = reduce(lambda x,y: f"{x}+'-'+{y}", qry['match'])                 # '(studyepoch:StudyEpoch)-[r1:`HAS_EPOCH`]->(cttermroot_has_epoch_1:CTTermRoot)...'
            f = re.findall(r'\((.*?)\)',e )                                     # ['studyepoch:StudyEpoch', 'cttermroot_has_epoch...CTTermRoot', 'studyepoch:StudyEpoch',...'
            dic = dict(map(lambda x: tuple(x.split(':'))  , f ))                # {'studyepoch': 'StudyEpoch', 'cttermroot_has_epoch_1': 'CTTermRoot', ...'
            # print (dic)
            if dic != {}:
                # print(f"where treatment: ")
                c = re.split( '=', qry['where'][0])                           # ['studyroot_study_root_1.uid ', ' $studyroot_study_ro...s_deleted ', ' $studyepoch_is_deleted_1']
                a = list(filter (lambda x: '.' in x, c ))                           # ['studyroot_study_root_1.uid ', ' $studyroot_study_ro...s_deleted ']
                g = list(map( lambda x: re.findall(r'\w+\.\w+',x )[0]  , a))        # ['studyroot_study_root_1.uid', 'studyepoch.is_deleted']
                b = list(map(lambda x: x.split('.'), g ))                           # [['studyroot_study_root_1', 'uid'], ['studyepoch', 'is_deleted']]
                log_list.append([ [dic[b[ith][0]], b[ith][1]] for ith in range(len(b))])  # [['StudyRoot', 'uid'], ['StudyEpoch', 'is_deleted']]
    except:
        pass


# %%
log_list_aux = list(filter (lambda x: x != [] , log_list))
log_list_aux = list(map (lambda x: x[0] , log_list_aux))
# %%
df_log = pd.DataFrame(log_list_aux)

#%%
df_log.set_axis(['one', 'two'], axis = 1, inplace = True )

# %%
grouped_by = df_log.groupby(['one', 'two']).size().reset_index().rename({0:"counting"}, axis = 1).sort_values('counting', ascending= False)
grouped_by.head()

#%%

# grouped_by.to_csv('freq_properties_labels2.csv')
#%%
# %%
grouped_by.apply(lambda x: f" CREATE INDEX ON :{x.one}({x.two})" if  x.counting>100 else None , axis = 1)

# CREATE CONSTRAINT [constraint_name] [IF NOT EXISTS]
# FOR (n:LabelName)
# REQUIRE n.propertyName IS [NODE] UNIQUE
# [OPTIONS "{" option: value[, ...] "}"]

# %% COMPLEX INDEXING #######################################################################
"""
WE ARE GOING TO TRY TO FETCH THOSE FULL TEXT AND THOSE COMBINED
"""
#%% imports
import pandas as pd 
import re
from functools import reduce
import copy
import json
log_path = './neo4j-mdr-db/neo4j/logs'
#%% load methods
def javascript_params_to_dict(parameters_sting:str):
    """this method fetch a javascript dict (without quotes on the key) and convert it into a json dict
    """
    text_replaced = re.sub(r'\'', r'"', parameters_sting ) #get strings
    text_replaced_2 = re.sub(r'<|>', r'"', text_replaced ) #get <null signs
    text_replaced_3 = re.sub(r' (\w+):', r'"\1":', text_replaced_2 ) #get nested keys
    parameters_dict = re.sub(r'{(\w+):', r'{"\1":', text_replaced_3 ) #get keys with {
    # print(parameters_dict)
    try:
        return json.loads(parameters_dict)
    except:
        print("error in parameters")

def from_corpus_to_where_queries(corpus:str):
    """" method to retreive splitted queries that contain where filtering
    """
    sub_corpus = re.sub(r'\n', ' ', corpus) # delete any carriage return
    # each_info = sub_corpus.split('+0000 INFO') # split the corpus by INFO (begining of the query)
    each_info = re.findall('(?s)\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}\+\d{4}.*?(?=\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}\+\d{4}|$)', 
                        sub_corpus) #split by each query time
    print(f"qnty of queries made: {len(each_info)}") #print 
    wh_query_list = list(filter (lambda x: 'WHERE' in x, each_info)) # filter just those queries that make a where filtering
    print("number of queries with where filtering: ", len(wh_query_list)) 
    # print(wh_query_list[-1:]) #print last query with where
    return wh_query_list
# %% extract text and get where list
with (open(f'./query_copy.log',encoding='ISO-8859-1') ) as f:
    #take the corpus of the file
    corpus = f.read()
wh_query_list = from_corpus_to_where_queries(corpus) #extract queries with where clases

#%% initialize queries list
log_list_dict = []
log_list = []
queries = []
#%%
def extract_query_metadata(i_th:str):
    # extract timestamp
    t_stamp = re.findall('\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}\+\d{4}', i_th) #match timestamp
    t_stamp = t_stamp[0].replace(' ','T') #make it iso standard
    print(f'timestamp : {t_stamp}')
    if t_stamp == '2023-02-13T11:33:07.238+0000':
        print("stop")

    # create a list of every cypher keyword text
    lines = re.sub(r'MATCH', r'\nMATCH ', i_th) 
    lines = re.sub(r'RETURN', r'\nRETURN ', lines)
    lines = re.sub(r'WITH', r'\nWITH ', lines)
    lines = re.sub(r'WHERE', r'\nWHERE ', lines) 
    lines = re.sub(r'MERGE', r'\nMERGE ', lines)
    lines = re.sub(r'SET', r'\nSET ', lines)
    lines = re.sub(r'CREATE', r'\nCREATE ', lines)
    lines_array = lines.split('\n')
    
    #extract parameters of the query
    # print(lines_array[-1]) #example of the end of the list of keywords
    parameters = re.findall('(?s)\{\w.*?(?= - runtime|$)', lines_array[-1]) #extract all the parameters dictionary
    if parameters:
        match_parameters = parameters[0] 
        parameters_dict = javascript_params_to_dict(match_parameters) #convert them as a json dictionary
    else:
        parameters_dict = {}
    
    #collect match and where lines
    match = list(filter (lambda x: 'MATCH' in x, lines_array)) # collect all the match keywords elements of the lines_array
    where = list(filter (lambda x: 'WHERE' in x, lines_array)) # collect all the match keywords elements of the lines_array

    # create a match dictionary in order to have (parameter_name,label)
    match_dict = {}
    query_description = ""
    if match:
        e = reduce(lambda x,y: f"{x}+'-'+{y}", match)                 # '(studyepoch:StudyEpoch)-[r1:`HAS_EPOCH`]->(cttermroot_has_epoch_1:CTTermRoot)...'
        f = re.findall(r'\((\b\w+\b\s*[: ]\s*\b\w+\b)\)',e) #re.findall(r'\((.*?)\)',e )                                     # ['studyepoch:StudyEpoch', 'cttermroot_has_epoch...CTTermRoot', 'studyepoch:StudyEpoch',...'
        z = list(filter (lambda x: ':' in x and not '{'in x, f)) # filter just those with ':' but not with '{' inside
        try:
            match_dict = dict(map(lambda x: tuple(x.split(':'))  , z ))   # {'studyepoch': 'StudyEpoch', 'cttermroot_has_epoch_1': 'CTTermRoot', ...'
        except:
            print("error in match")
            query_description = " ERROR in match"

    return t_stamp, parameters_dict, match, where, match_dict, query_description

 # FOR every query
for i_th in wh_query_list:
        
    qry = {} #create query metadata dictionary 
    qry['time_stamp'], qry['parameters_dict'], qry['match'], qry['where'], qry['match_dict'], qry['query_description'] = extract_query_metadata(i_th)
    # print(qry)

    if qry['match_dict'] == {}:
        qry['query_description'] = qry['query_description']+ ", NO MATCH CLAUSE"
        #pass to the next query because there are no match ---> no match no useful wheres 
    else:
        qry['query_description'] = "MATCH OK"
        #for each where extract its conditions
        wheres = []
        for i_where in qry['where']:

            #extract conditions list from where
            a = re.sub('WHERE ', '', i_where) 
            c = re.split( 'AND|OR', a)            
            c_2 = list(filter(lambda x: 'id(' not in x and 'ID(' not in x, c))

            ##%%
            conditions = [] #list of condition's dictionary
            for i_condition in c_2:
                condition = {}
                cond_strip = i_condition.strip()
                condition_match = re.findall('(=|<=|>=|<|>|CONTAINS|contains|=~|IS|is)', cond_strip)
                if condition_match:
                    condition['equality'] = condition_match[0]
                else:
                    print("there's an error on matching equalities")
                    print(qry)
                    print(condition_match)
                    condition['equality'] = 'NA'
                    qry['query_description'] = qry['query_description']+ ", error there's no condition_match"
                    # raise Exception('spam', 'eggs')
                cond_split = re.split('=|<=|>=|<|>|CONTAINS|contains|=~|IS|is', cond_strip)
                hypothesis = list(
                    filter(lambda x: 
                        "'" in x or 
                        '`' in x or 
                        '$' in x,
                        cond_split
                    ))
                if hypothesis and qry['parameters_dict']: 
                    condition['hypothesis'] = hypothesis[0].strip() 
                    condition['hypothesis'] = re.sub('\$', '', condition['hypothesis'])
                    condition['hypothesis'] = qry['parameters_dict'][condition['hypothesis']] if condition['hypothesis'] in qry['parameters_dict'].keys() else condition['hypothesis']
                else:
                    qry['query_description'] = qry['query_description']+ ", error there's no parameters_dict or hypothesis"
                    condition['hypothesis'] = 'NA'
                ident_statement = list(
                    filter(lambda x: 
                        '.' in x and 
                        (
                            "'" not in x or 
                            '`' not in x or 
                            '$' not in x
                        ), 
                        cond_split  
                    ))
                if ident_statement:
                    ident_statement_split = ident_statement[0].strip().split('.')
                    ident_statement_split
                    condition['identifier'] = ident_statement_split[0]
                    condition['identifier'] = qry['match_dict'][condition['identifier']] if condition['identifier'] in qry['match_dict'].keys() else 'NA'
                else:
                    condition['identifier'] = 'NA'
                    qry['query_description'] = qry['query_description']+ ", error there's no identifier statement"
                condition['property'] = ident_statement_split[1]
                try:
                    condition['full_text_flag'] = ('True' if ' ' in condition['hypothesis'] or '`' in condition['hypothesis'] or "'" in condition['hypothesis'] else 'False')
                except:
                    print("ERROR in hypothesis")
                    qry['query_description'] = qry['query_description']+ ", ERROR in hypothesis"
                conditions.append(copy.deepcopy(condition))
            wheres.append(copy.deepcopy(conditions))
        qry['parsed_wheres'] = copy.deepcopy(wheres)
    queries.append(copy.deepcopy(qry))
        


# %%

#%%
# df_queries = pd.DataFrame()
matrix = []
for query_idx, i_query in enumerate(queries):
    if i_query.get('parsed_wheres'):
        for where_idx, i_where in enumerate(i_query['parsed_wheres']):
            for condition_idx, i_condition in enumerate(i_where):
                matrix.append(
                    [
                        query_idx, 
                        where_idx,
                        condition_idx,
                        i_condition['identifier'], 
                        i_condition['property'], 
                        i_condition['equality'],
                        i_condition['hypothesis']
                    ]
                )

# matrix
#%%
df_queries = pd.DataFrame(matrix, columns = ['query_id', 'where_id', 'condition_id', 'label','property','equality','hypothesis'])
df_queries
#%%
frequencies = df_queries.groupby(['label', 'property']).size().reset_index().rename({0:"counting"}, axis = 1).sort_values('counting', ascending= False)
#%%
frequencies

#%%PARSING ERRORS ANALYSIS
for i_query in df_queries[df_queries.label == 'NA'].query_id.values:
    
    print(queries[i_query])

# %%
([print(i[0]) if len(i)>0 else None for i in parameters_array])
# %%
parameters_array
# %%
for i in parameters_array:
    print (i[0])
    ast.literal_eval(i[0])
# %%
def parse_nested_dict(d):
  for key, value in d.items():
    if isinstance(value, dict):
      parse_nested_dict(value)
    else:
      print(key, value)
#%%
d = {
  "a": 1,
  "b": {
    "c": 2,
    "d": {
      "e": 3
    }
  }
}
#%%

for key, value in d.items():
    if isinstance(value, dict):
      parse_nested_dict(value)
    else:
      print(key, value)

#%%
import ast
# %%
\b(\w+):
#%%
parameters_with_commas = re.sub(r'\b(\w+):', r'"\1"', parameters_array)
            
# %%
parameters_with_commas
# %%
parameters_no_empty = list(filter(lambda x: len(x)>0, parameters_array))
#%%
parameters_dict_array=[]
for i in parameters_no_empty:
    # print(i[0])
    text_replaced = re.sub(r'\'', r'"', i[0] )
    text_replaced_2 = re.sub(r'<|>', r'"', text_replaced )
    text_replaced_3 = re.sub(r' (\w+):', r'"\1":', text_replaced_2 )
    parameters_dict = re.sub(r'{(\w+):', r'{"\1":', text_replaced_3 )
    # print(parameters_dict)
    parameters_dict_2 = re.sub(r':\ (\d+(\.\d+)?)\b', r':"\1"', parameters_dict)
    # print(parameters_dict_2)
    parameters_dict_cast = json.loads(parameters_dict)
    parameters_dict_array.append(parameters_dict_cast)
# %%
parameters_dict_array
# %%
json.loads(parameters_no_empty[0][0], skipkeys = True)


# %% USE DEMJSON IF YOU HAVE 3.10
# import demjson
# import json

# #%%
# # input JavaScript object
# x = "{ version: '2.1.2', dipa: '1.2.3.4', dipaType: '', customerInfo: [{ name: 'xyz', id: 1234, account_id: 'abc', contract_id: 'abc', in_use: true, region: 'NA', location: 'USA' }, { name: 'XYZ', id: 9644, account_id: 'qwerty5', contract_id: 'qscdfgr', in_use: true, region: 'NA', location: 'cambridge' } ], maxAlertCount: 2304, onEgress: false, scrubCenters: [{ name: 'TO', percentage: 95.01, onEgress: false }], state: 'update', updated: '1557950465', vectors: [{ name: 'rate', alertNames: ['rate'], onEgress: false, Alerts: [{ key: '1.2.3.4', source: 'eve', eNew: '1557943443', dc: 'TOP2', bond: 'Border', percentage: 95.01, gress: 'ingress', sourceEpochs: ['1557950408', '1557950411', '1557950414', '1557950417', '1557950420', '1557950423', '1557950426', '1557950429', '1557950432', '1557950435', '1557950438', '1557950441', '1557950444', '1557950447', '1557950450', '1557950453', '1557950456', '1557950459', '1557950462', '1557950465' ], name: 'rate', category: 'rate', level: 'alarm', data_type: 'value', data: 19.99, timestamp: 1557950466, type: 'alert', value: 95.01, eUpdated: '1557950465' }], dcs: ['TO'], bonds: ['Bo'] }, { name: 'udp', alertNames: ['udp'], onEgress: false, Alerts: [{ key: '1.2.3.4', source: 'top', eNew: '1557943500', dc: 'TO', bond: 'Bo', percentage: 95.01, gress: 'ingress', sourceEpochs: ['1557950408', '1557950411', '1557950414', '1557950417', '1557950420', '1557950423', '1557950426', '1557950429', '1557950432', '1557950435', '1557950438', '1557950441', '1557950444', '1557950447', '1557950450', '1557950453', '1557950456', '1557950459', '1557950462', '1557950465' ], name: 'udp', category: 'udp', level: 'alert', data_type: 'named_values_list', data: [{ name: 'Dst', value: 25 }], timestamp: 1557950466, type: 'alert', eUpdated: '1557950465' }], dcs: ['TO'], bonds: ['Bo'] }, { name: 'tcp', alertNames: ['tcp_condition'], onEgress: false, Alerts: [{ key: '1.2.3.4', source: 'to', eNew: '1557950354', dc: 'TO', bond: 'Bo', percentage: 95.01, gress: 'ingress', sourceEpochs: ['1557950360', '1557950363', '1557950366', '1557950372', '1557950384', '1557950387', '1557950396', '1557950399', '1557950411', '1557950417', '1557950423', '1557950426', '1557950432', '1557950441', '1557950444', '1557950447', '1557950450', '1557950456', '1557950459', '1557950465' ], name: 'tcp', category: 'tcp', level: 'alert', data_type: 'named', data: [{ name: 'TCP', value: 25 }], timestamp: 1557950466, type: 'alert', eUpdated: '1557950465' }], dcs: ['TO'], bonds: ['Bo'] } ], timestamps: { firstAlerted: '1557943443', lastAlerted: '1557950465', lastLeaked: null } }"

# # decode it into json data
# json_data = demjson.decode(x, "utf-8")
# # Return the 4 space indent the original had
# json_final = json.dumps(json_data, indent=4)
# print(json_final)

#%%
def javascript_params_to_dict(parameters_sting:str):
    # print(i[0])
    text_replaced = re.sub(r'\'', r'"', parameters_sting )
    text_replaced_2 = re.sub(r'<|>', r'"', text_replaced )
    text_replaced_3 = re.sub(r' (\w+):', r'"\1":', text_replaced_2 )
    parameters_dict = re.sub(r'{(\w+):', r'{"\1":', text_replaced_3 )
    # print(parameters_dict)
    return json.loads(parameters_dict)
# %% labes that contains nodes with uid property, that don't contain Study

"""
match (n) 
where not n.uid is null 
unwind labels(n) as labels_unw
with labels_unw 
where labels_unw contains 'Root'

return collect( distinct labels_unw)"""

#%%
indexes = [
        "TemplateParameterValueRoot",
        "CTCodelistRoot",
        "CTTermRoot",
        "CTTermNameRoot",
        "DictionaryCodelistRoot",
        "DictionaryTermRoot",
        "SnomedTermRoot",
        "MEDRTTermRoot",
        "UCUMTermRoot",
        "UNIITermRoot",
        "CTConfigRoot",
        "ConceptRoot",
        "UnitDefinitionRoot",
        "ActivityGroupRoot",
        "ActivitySubGroupRoot",
        "ActivityRoot",
        "ActivityInstanceRoot",
        "CategoricFindingRoot",
        "FindingRoot",
        "NumericFindingRoot",
        "EventRoot",
        "TextualFindingRoot",
        "NumericValueRoot",
        "LagTimeRoot",
        "SimpleConceptRoot",
        "NumericValueWithUnitRoot",
        "CompoundRoot",
        "CompoundAliasRoot",
        "OdmTemplateRoot",
        "OdmDescriptionRoot",
        "OdmFormRoot",
        "OdmItemGroupRoot",
        "OdmItemRoot",
        "OdmAliasRoot",
        "StudyRoot",
        "ObjectiveTemplateRoot",
        "ObjectiveRoot",
        "EndpointTemplateRoot",
        "EndpointRoot",
        "TimeframeTemplateRoot",
        "TimeframeRoot",
        "StudyDayRoot",
        "StudyDurationDaysRoot",
        "StudyDurationWeeksRoot",
        "StudyWeekRoot",
        "VisitNameRoot",
        "CriteriaTemplateRoot",
        "TimePointRoot",
        "CriteriaRoot",
        'CTCodelistAttributesRoot', 'CTCodelistNameRoot', 'CTTermAttributesRoot'
      ]
#%%
df_indexes = pd.DataFrame(indexes, columns = ['label'])
#%%
# accu = []
#%%
# accu.extend(list(map(lambda x: f'CREATE CONSTRAINT constraint_{x} ON (node:{x}) ASSERT node.uid IS UNIQUE', indexes)))
#%%

df_indexes.apply(lambda x: print(f" 'CREATE CONSTRAINT constraint_{x.label} ON (node:{x.label}) ASSERT node.uid IS UNIQUE'," ), axis = 1)

#%%

df_indexes.apply(lambda x: print(f'("{x.label}", "uid", True),' ), axis = 1)
# %%
#%% labes that contains nodes with uid property, that don't contain Root and don't contain Study
indexes = ["CTPackage", 
            "CTPackageCodelist", 
            "CTPackageTerm", 
            "ActivityDefinition", 
            "ActivityItem", 
            "ClinicalProgramme", 
            "Project"]

#%%
df_indexes = pd.DataFrame(indexes, columns = ['label'])
#%%
df_indexes.apply(lambda x: print(f" 'CREATE CONSTRAINT constraint_{x.label} ON (node:{x.label}) ASSERT node.uid IS UNIQUE'," ), axis = 1)
#%%

df_indexes.apply(lambda x: print(f'("{x.label}", "uid", True),' ), axis = 1)
# %%labes that contains nodes with uid property, that are studies, impling to not to be unique
"""match (n) 
where not n.uid is null 
unwind labels(n) as labels_unw
with labels_unw 
where  not labels_unw contains 'Root' and labels_unw contains 'Study'

return collect( distinct labels_unw)"""
#%% 
indexes = [
        "StudyEpoch",
        "OrderedStudySelection",
        "StudySelection",
        "StudyVisit",
        "StudyArm",
        "StudyCohort",
        "StudyElement",
        "StudyDesignCell",
        "StudyActivity",
        "StudyCriteria",
        "StudyObjective",
        "StudyEndpoint",
        "StudyCompound",
        "StudyActivitySchedule",
        "StudyBranchArm",
        "StudyDiseaseMilestone",
        "OrderedStudySelectionDiseaseMilestone"
      ]



#%%
df_indexes = pd.DataFrame(indexes, columns = ['label'])
#%%
df_indexes.apply(lambda x: print(f" 'CREATE INDEX index_{x.label} IF NOT EXISTS FOR (n:{x.label}) ON (n.uid)'," ), axis = 1)
#%%

df_indexes.apply(lambda x: print(f'("{x.label}", "uid"),' ), axis = 1)

# %%
"""match (n) 
where not n.name is null 
unwind labels(n) as labels_unw
with labels_unw 
where  not labels_unw contains 'Value' and not labels_unw contains 'Study'

return collect( distinct labels_unw)"""
#%%
indexes = [
        "TemplateParameter",
        "Library",
        "CTCatalogue",
        "CTPackage",
        "ClinicalProgramme",
        "Project",
        "Brand"
      ]
#%%
df_indexes = pd.DataFrame(indexes, columns = ['label'])
#%%
df_indexes.apply(lambda x: print(f" 'CREATE TEXT INDEX index_name_{x.label} FOR (n:{x.label}) ON (n.name)'," ), axis = 1)
#%%

df_indexes.apply(lambda x: print(f'("{x.label}", "name"),' ), axis = 1)
# %%
"""match (n) 
where not n.name is null 
unwind labels(n) as labels_unw
with labels_unw 
where   labels_unw contains 'Value'

return collect( distinct labels_unw)
"""
#%%

indexes = [
        "TemplateParameterValue",
        "CTCodelistAttributesValue",
        "CTCodelistNameValue",
        "CTTermNameValue",
        "DictionaryCodelistValue",
        "SnomedTermValue",
        "DictionaryTermValue",
        "MEDRTTermValue",
        "UCUMTermValue",
        "UNIITermValue",
        "UnitDefinitionValue",
        "ConceptValue",
        "ActivityGroupValue",
        "ActivitySubGroupValue",
        "ActivityValue",
        "ActivityInstanceValue",
        "CategoricFindingValue",
        "FindingValue",
        "NumericFindingValue",
        "EventValue",
        "TextualFindingValue",
        "LagTimeValue",
        "NumericValue",
        "SimpleConceptValue",
        "NumericValueWithUnitValue",
        "CompoundValue",
        "CompoundAliasValue",
        "OdmVendorNamespaceValue",
        "OdmVendorAttributeValue",
        "OdmTemplateValue",
        "OdmDescriptionValue",
        "OdmFormValue",
        "OdmItemGroupValue",
        "OdmItemValue",
        "OdmAliasValue",
        "ObjectiveTemplateValue",
        "ObjectiveValue",
        "EndpointTemplateValue",
        "EndpointValue",
        "TimeframeTemplateValue",
        "TimeframeValue",
        "StudyDayValue",
        "StudyDurationDaysValue",
        "StudyDurationWeeksValue",
        "StudyWeekValue",
        "VisitNameValue",
        "CriteriaTemplateValue",
        "TimePointValue",
        "CriteriaValue",
        "ActivityDescriptionTemplateValue"
      ]

#%%
df_indexes = pd.DataFrame(indexes, columns = ['label'])
#%%
df_indexes.apply(lambda x: print(f" 'CREATE INDEX index_name_{x.label} FOR (n:{x.label}) ON (n.name)'," ), axis = 1)
#%%

df_indexes.apply(lambda x: print(f'("{x.label}", "name"),' ), axis = 1)

#%%
"CREATE INDEX index_CTTermAttributesValue_code IF NOT EXISTS FOR (n:CTTermAttributesValue) ON (n.code_submission_value)",
"CREATE INDEX index_CTTermAttributesValue_name IF NOT EXISTS FOR (n:CTTermAttributesValue) ON (n.name_submission_value)",
"CREATE INDEX index_StudyFieldName IF NOT EXISTS FOR (n:StudyField) ON (n.field_name)",



("CTTermAttributesValue","code_submission_value")
("CTTermAttributesValue","name_submission_value")
("StudyField","field_name")


# %% asdjfljasd;lfjkasd;lfkjasd;lfkjas;dflkjasdf;lkjasdf;laksjdf


# queries = []

# labels = [
#     "TemplateParameterValueRoot",
#     "CTCodelistRoot",
#     "CTTermRoot",
#     "CTTermNameRoot",
#     "DictionaryCodelistRoot",
#     "DictionaryTermRoot",
#     "SnomedTermRoot",
#     "MEDRTTermRoot",
#     "UCUMTermRoot",
#     "UNIITermRoot",
#     "CTConfigRoot",
#     "ConceptRoot",
#     "UnitDefinitionRoot",
#     "ActivityGroupRoot",
#     "ActivitySubGroupRoot",
#     "ActivityRoot",
#     "ActivityInstanceRoot",
#     "CategoricFindingRoot",
#     "FindingRoot",
#     "NumericFindingRoot",
#     "EventRoot",
#     "TextualFindingRoot",
#     "NumericValueRoot",
#     "LagTimeRoot",
#     "SimpleConceptRoot",
#     "NumericValueWithUnitRoot",
#     "CompoundRoot",
#     "CompoundAliasRoot",
#     "OdmTemplateRoot",
#     "OdmDescriptionRoot",
#     "OdmFormRoot",
#     "OdmItemGroupRoot",
#     "OdmItemRoot",
#     "OdmAliasRoot",
#     "StudyRoot",
#     "ObjectiveTemplateRoot",
#     "ObjectiveRoot",
#     "EndpointTemplateRoot",
#     "EndpointRoot",
#     "TimeframeTemplateRoot",
#     "TimeframeRoot",
#     "StudyDayRoot",
#     "StudyDurationDaysRoot",
#     "StudyDurationWeeksRoot",
#     "StudyWeekRoot",
#     "VisitNameRoot",
#     "CriteriaTemplateRoot",
#     "TimePointRoot",
#     "CriteriaRoot",
#     'CTCodelistAttributesRoot', 'CTCodelistNameRoot', 'CTTermAttributesRoot'
#     ]
# queries.extend(list(map(lambda x: f'CREATE CONSTRAINT constraint_{x} ON (node:{x}) ASSERT node.uid IS UNIQUE', labels)))

# labels = ["CTPackage", 
#             "CTPackageCodelist", 
#             "CTPackageTerm", 
#             "ActivityDefinition", 
#             "ActivityItem", 
#             "ClinicalProgramme", 
#             "Project"]

# queries.extend(list(map(lambda x: f"CREATE CONSTRAINT constraint_{x} ON (node:{x}) ASSERT node.uid IS UNIQUE", labels)))

# labels = [
#         "StudyEpoch",
#         "OrderedStudySelection",
#         "StudySelection",
#         "StudyVisit",
#         "StudyArm",
#         "StudyCohort",
#         "StudyElement",
#         "StudyDesignCell",
#         "StudyActivity",
#         "StudyCriteria",
#         "StudyObjective",
#         "StudyEndpoint",
#         "StudyCompound",
#         "StudyActivitySchedule",
#         "StudyBranchArm",
#         "StudyDiseaseMilestone",
#         "OrderedStudySelectionDiseaseMilestone"
#       ]

# #%%
# queries.extend(list(map(lambda x: f"CREATE INDEX index_{x} IF NOT EXISTS FOR (n:{x}) ON (n.uid)", labels)))
# # %%

# labels = [
#         "TemplateParameter",
#         "Library",
#         "CTCatalogue",
#         "CTPackage",
#         "ClinicalProgramme",
#         "Project",
#         "Brand"
#       ]

# queries.extend(list(map(lambda x: f"CREATE TEXT INDEX index_name_{x} FOR (n:{x}) ON (n.name)", labels)))



# labels = [
#         "TemplateParameterValue",
#         "CTCodelistAttributesValue",
#         "CTCodelistNameValue",
#         "CTTermNameValue",
#         "DictionaryCodelistValue",
#         "SnomedTermValue",
#         "DictionaryTermValue",
#         "MEDRTTermValue",
#         "UCUMTermValue",
#         "UNIITermValue",
#         "UnitDefinitionValue",
#         "ConceptValue",
#         "ActivityGroupValue",
#         "ActivitySubGroupValue",
#         "ActivityValue",
#         "ActivityInstanceValue",
#         "CategoricFindingValue",
#         "FindingValue",
#         "NumericFindingValue",
#         "EventValue",
#         "TextualFindingValue",
#         "LagTimeValue",
#         "NumericValue",
#         "SimpleConceptValue",
#         "NumericValueWithUnitValue",
#         "CompoundValue",
#         "CompoundAliasValue",
#         "OdmVendorNamespaceValue",
#         "OdmVendorAttributeValue",
#         "OdmTemplateValue",
#         "OdmDescriptionValue",
#         "OdmFormValue",
#         "OdmItemGroupValue",
#         "OdmItemValue",
#         "OdmAliasValue",
#         "ObjectiveTemplateValue",
#         "ObjectiveValue",
#         "EndpointTemplateValue",
#         "EndpointValue",
#         "TimeframeTemplateValue",
#         "TimeframeValue",
#         "StudyDayValue",
#         "StudyDurationDaysValue",
#         "StudyDurationWeeksValue",
#         "StudyWeekValue",
#         "VisitNameValue",
#         "CriteriaTemplateValue",
#         "TimePointValue",
#         "CriteriaValue",
#         "ActivityDescriptionTemplateValue"
#       ]

# queries.extend(list(map(lambda x: f"CREATE INDEX index_name_{x} FOR (n:{x}) ON (n.name)", labels)))


# # %%


for querystring in [
        # clinical-mdr-api
        # -----------------------------------------------------------------------------------------------------------------------
        "CALL apoc.schema.assert({},{})",
        "CREATE INDEX index_CTTermAttributesValue_code IF NOT EXISTS FOR (n:CTTermAttributesValue) ON (n.code_submission_value)",
        "CREATE INDEX index_CTTermAttributesValue_name IF NOT EXISTS FOR (n:CTTermAttributesValue) ON (n.name_submission_value)",
        "CREATE INDEX index_StudyFieldName IF NOT EXISTS FOR (n:StudyField) ON (n.field_name)",

        'CREATE INDEX index_StudyEpoch IF NOT EXISTS FOR (n:StudyEpoch) ON (n.uid)',
        'CREATE INDEX index_OrderedStudySelection IF NOT EXISTS FOR (n:OrderedStudySelection) ON (n.uid)',
        'CREATE INDEX index_StudySelection IF NOT EXISTS FOR (n:StudySelection) ON (n.uid)',
        'CREATE INDEX index_StudyVisit IF NOT EXISTS FOR (n:StudyVisit) ON (n.uid)',
        'CREATE INDEX index_StudyArm IF NOT EXISTS FOR (n:StudyArm) ON (n.uid)',
        'CREATE INDEX index_StudyCohort IF NOT EXISTS FOR (n:StudyCohort) ON (n.uid)',
        'CREATE INDEX index_StudyElement IF NOT EXISTS FOR (n:StudyElement) ON (n.uid)',
        'CREATE INDEX index_StudyDesignCell IF NOT EXISTS FOR (n:StudyDesignCell) ON (n.uid)',
        'CREATE INDEX index_StudyActivity IF NOT EXISTS FOR (n:StudyActivity) ON (n.uid)',
        'CREATE INDEX index_StudyCriteria IF NOT EXISTS FOR (n:StudyCriteria) ON (n.uid)',
        'CREATE INDEX index_StudyObjective IF NOT EXISTS FOR (n:StudyObjective) ON (n.uid)',
        'CREATE INDEX index_StudyEndpoint IF NOT EXISTS FOR (n:StudyEndpoint) ON (n.uid)',
        'CREATE INDEX index_StudyCompound IF NOT EXISTS FOR (n:StudyCompound) ON (n.uid)',
        'CREATE INDEX index_StudyActivitySchedule IF NOT EXISTS FOR (n:StudyActivitySchedule) ON (n.uid)',
        'CREATE INDEX index_StudyBranchArm IF NOT EXISTS FOR (n:StudyBranchArm) ON (n.uid)',
        'CREATE INDEX index_StudyDiseaseMilestone IF NOT EXISTS FOR (n:StudyDiseaseMilestone) ON (n.uid)',
        'CREATE INDEX index_OrderedStudySelectionDiseaseMilestone IF NOT EXISTS FOR (n:OrderedStudySelectionDiseaseMilestone) ON (n.uid)',

        'CREATE CONSTRAINT constraint_CTPackage ON (node:CTPackage) ASSERT node.uid IS UNIQUE',
        'CREATE CONSTRAINT constraint_CTPackageCodelist ON (node:CTPackageCodelist) ASSERT node.uid IS UNIQUE',
        'CREATE CONSTRAINT constraint_CTPackageTerm ON (node:CTPackageTerm) ASSERT node.uid IS UNIQUE',
        'CREATE CONSTRAINT constraint_ActivityDefinition ON (node:ActivityDefinition) ASSERT node.uid IS UNIQUE',
        'CREATE CONSTRAINT constraint_ActivityItem ON (node:ActivityItem) ASSERT node.uid IS UNIQUE',
        'CREATE CONSTRAINT constraint_ClinicalProgramme ON (node:ClinicalProgramme) ASSERT node.uid IS UNIQUE',
        'CREATE CONSTRAINT constraint_Project ON (node:Project) ASSERT node.uid IS UNIQUE',

        'CREATE CONSTRAINT constraint_TemplateParameterValueRoot ON (node:TemplateParameterValueRoot) ASSERT node.uid IS UNIQUE',
        'CREATE CONSTRAINT constraint_CTCodelistRoot ON (node:CTCodelistRoot) ASSERT node.uid IS UNIQUE',
        'CREATE CONSTRAINT constraint_CTTermRoot ON (node:CTTermRoot) ASSERT node.uid IS UNIQUE',
        'CREATE CONSTRAINT constraint_CTTermNameRoot ON (node:CTTermNameRoot) ASSERT node.uid IS UNIQUE',
        'CREATE CONSTRAINT constraint_DictionaryCodelistRoot ON (node:DictionaryCodelistRoot) ASSERT node.uid IS UNIQUE',
        'CREATE CONSTRAINT constraint_DictionaryTermRoot ON (node:DictionaryTermRoot) ASSERT node.uid IS UNIQUE',
        'CREATE CONSTRAINT constraint_SnomedTermRoot ON (node:SnomedTermRoot) ASSERT node.uid IS UNIQUE',
        'CREATE CONSTRAINT constraint_MEDRTTermRoot ON (node:MEDRTTermRoot) ASSERT node.uid IS UNIQUE',
        'CREATE CONSTRAINT constraint_UCUMTermRoot ON (node:UCUMTermRoot) ASSERT node.uid IS UNIQUE',
        'CREATE CONSTRAINT constraint_UNIITermRoot ON (node:UNIITermRoot) ASSERT node.uid IS UNIQUE',
        'CREATE CONSTRAINT constraint_CTConfigRoot ON (node:CTConfigRoot) ASSERT node.uid IS UNIQUE',
        'CREATE CONSTRAINT constraint_ConceptRoot ON (node:ConceptRoot) ASSERT node.uid IS UNIQUE',
        'CREATE CONSTRAINT constraint_UnitDefinitionRoot ON (node:UnitDefinitionRoot) ASSERT node.uid IS UNIQUE',
        'CREATE CONSTRAINT constraint_ActivityGroupRoot ON (node:ActivityGroupRoot) ASSERT node.uid IS UNIQUE',
        'CREATE CONSTRAINT constraint_ActivitySubGroupRoot ON (node:ActivitySubGroupRoot) ASSERT node.uid IS UNIQUE',
        'CREATE CONSTRAINT constraint_ActivityRoot ON (node:ActivityRoot) ASSERT node.uid IS UNIQUE',
        'CREATE CONSTRAINT constraint_ActivityInstanceRoot ON (node:ActivityInstanceRoot) ASSERT node.uid IS UNIQUE',
        'CREATE CONSTRAINT constraint_CategoricFindingRoot ON (node:CategoricFindingRoot) ASSERT node.uid IS UNIQUE',
        'CREATE CONSTRAINT constraint_FindingRoot ON (node:FindingRoot) ASSERT node.uid IS UNIQUE',
        'CREATE CONSTRAINT constraint_NumericFindingRoot ON (node:NumericFindingRoot) ASSERT node.uid IS UNIQUE',
        'CREATE CONSTRAINT constraint_EventRoot ON (node:EventRoot) ASSERT node.uid IS UNIQUE',
        'CREATE CONSTRAINT constraint_TextualFindingRoot ON (node:TextualFindingRoot) ASSERT node.uid IS UNIQUE',
        'CREATE CONSTRAINT constraint_NumericValueRoot ON (node:NumericValueRoot) ASSERT node.uid IS UNIQUE',
        'CREATE CONSTRAINT constraint_LagTimeRoot ON (node:LagTimeRoot) ASSERT node.uid IS UNIQUE',
        'CREATE CONSTRAINT constraint_SimpleConceptRoot ON (node:SimpleConceptRoot) ASSERT node.uid IS UNIQUE',
        'CREATE CONSTRAINT constraint_NumericValueWithUnitRoot ON (node:NumericValueWithUnitRoot) ASSERT node.uid IS UNIQUE',
        'CREATE CONSTRAINT constraint_CompoundRoot ON (node:CompoundRoot) ASSERT node.uid IS UNIQUE',
        'CREATE CONSTRAINT constraint_CompoundAliasRoot ON (node:CompoundAliasRoot) ASSERT node.uid IS UNIQUE',
        'CREATE CONSTRAINT constraint_OdmTemplateRoot ON (node:OdmTemplateRoot) ASSERT node.uid IS UNIQUE',
        'CREATE CONSTRAINT constraint_OdmDescriptionRoot ON (node:OdmDescriptionRoot) ASSERT node.uid IS UNIQUE',
        'CREATE CONSTRAINT constraint_OdmFormRoot ON (node:OdmFormRoot) ASSERT node.uid IS UNIQUE',
        'CREATE CONSTRAINT constraint_OdmItemGroupRoot ON (node:OdmItemGroupRoot) ASSERT node.uid IS UNIQUE',
        'CREATE CONSTRAINT constraint_OdmItemRoot ON (node:OdmItemRoot) ASSERT node.uid IS UNIQUE',
        'CREATE CONSTRAINT constraint_OdmAliasRoot ON (node:OdmAliasRoot) ASSERT node.uid IS UNIQUE',
        'CREATE CONSTRAINT constraint_StudyRoot ON (node:StudyRoot) ASSERT node.uid IS UNIQUE',
        'CREATE CONSTRAINT constraint_ObjectiveTemplateRoot ON (node:ObjectiveTemplateRoot) ASSERT node.uid IS UNIQUE',
        'CREATE CONSTRAINT constraint_ObjectiveRoot ON (node:ObjectiveRoot) ASSERT node.uid IS UNIQUE',
        'CREATE CONSTRAINT constraint_EndpointTemplateRoot ON (node:EndpointTemplateRoot) ASSERT node.uid IS UNIQUE',
        'CREATE CONSTRAINT constraint_EndpointRoot ON (node:EndpointRoot) ASSERT node.uid IS UNIQUE',
        'CREATE CONSTRAINT constraint_TimeframeTemplateRoot ON (node:TimeframeTemplateRoot) ASSERT node.uid IS UNIQUE',
        'CREATE CONSTRAINT constraint_TimeframeRoot ON (node:TimeframeRoot) ASSERT node.uid IS UNIQUE',
        'CREATE CONSTRAINT constraint_StudyDayRoot ON (node:StudyDayRoot) ASSERT node.uid IS UNIQUE',
        'CREATE CONSTRAINT constraint_StudyDurationDaysRoot ON (node:StudyDurationDaysRoot) ASSERT node.uid IS UNIQUE',
        'CREATE CONSTRAINT constraint_StudyDurationWeeksRoot ON (node:StudyDurationWeeksRoot) ASSERT node.uid IS UNIQUE',
        'CREATE CONSTRAINT constraint_StudyWeekRoot ON (node:StudyWeekRoot) ASSERT node.uid IS UNIQUE',
        'CREATE CONSTRAINT constraint_VisitNameRoot ON (node:VisitNameRoot) ASSERT node.uid IS UNIQUE',
        'CREATE CONSTRAINT constraint_CriteriaTemplateRoot ON (node:CriteriaTemplateRoot) ASSERT node.uid IS UNIQUE',
        'CREATE CONSTRAINT constraint_TimePointRoot ON (node:TimePointRoot) ASSERT node.uid IS UNIQUE',
        'CREATE CONSTRAINT constraint_CriteriaRoot ON (node:CriteriaRoot) ASSERT node.uid IS UNIQUE',
        'CREATE CONSTRAINT constraint_CTCodelistAttributesRoot ON (node:CTCodelistAttributesRoot) ASSERT node.uid IS UNIQUE',
        'CREATE CONSTRAINT constraint_CTCodelistNameRoot ON (node:CTCodelistNameRoot) ASSERT node.uid IS UNIQUE',
        'CREATE CONSTRAINT constraint_CTTermAttributesRoot ON (node:CTTermAttributesRoot) ASSERT node.uid IS UNIQUE',

        'CREATE TEXT INDEX index_name_TemplateParameter FOR (n:TemplateParameter) ON (n.name)',
        'CREATE TEXT INDEX index_name_Library FOR (n:Library) ON (n.name)',
        'CREATE TEXT INDEX index_name_CTCatalogue FOR (n:CTCatalogue) ON (n.name)',
        'CREATE TEXT INDEX index_name_CTPackage FOR (n:CTPackage) ON (n.name)',
        'CREATE TEXT INDEX index_name_ClinicalProgramme FOR (n:ClinicalProgramme) ON (n.name)',
        'CREATE TEXT INDEX index_name_Project FOR (n:Project) ON (n.name)',
        'CREATE TEXT INDEX index_name_Brand FOR (n:Brand) ON (n.name)',

        'CREATE INDEX index_name_TemplateParameterValue FOR (n:TemplateParameterValue) ON (n.name)',
        'CREATE INDEX index_name_CTCodelistAttributesValue FOR (n:CTCodelistAttributesValue) ON (n.name)',
        'CREATE INDEX index_name_CTCodelistNameValue FOR (n:CTCodelistNameValue) ON (n.name)',
        'CREATE INDEX index_name_CTTermNameValue FOR (n:CTTermNameValue) ON (n.name)',
        'CREATE INDEX index_name_DictionaryCodelistValue FOR (n:DictionaryCodelistValue) ON (n.name)',
        'CREATE INDEX index_name_SnomedTermValue FOR (n:SnomedTermValue) ON (n.name)',
        'CREATE INDEX index_name_DictionaryTermValue FOR (n:DictionaryTermValue) ON (n.name)',
        'CREATE INDEX index_name_MEDRTTermValue FOR (n:MEDRTTermValue) ON (n.name)',
        'CREATE INDEX index_name_UCUMTermValue FOR (n:UCUMTermValue) ON (n.name)',
        'CREATE INDEX index_name_UNIITermValue FOR (n:UNIITermValue) ON (n.name)',
        'CREATE INDEX index_name_UnitDefinitionValue FOR (n:UnitDefinitionValue) ON (n.name)',
        'CREATE INDEX index_name_ConceptValue FOR (n:ConceptValue) ON (n.name)',
        'CREATE INDEX index_name_ActivityGroupValue FOR (n:ActivityGroupValue) ON (n.name)',
        'CREATE INDEX index_name_ActivitySubGroupValue FOR (n:ActivitySubGroupValue) ON (n.name)',
        'CREATE INDEX index_name_ActivityValue FOR (n:ActivityValue) ON (n.name)',
        'CREATE INDEX index_name_ActivityInstanceValue FOR (n:ActivityInstanceValue) ON (n.name)',
        'CREATE INDEX index_name_CategoricFindingValue FOR (n:CategoricFindingValue) ON (n.name)',
        'CREATE INDEX index_name_FindingValue FOR (n:FindingValue) ON (n.name)',
        'CREATE INDEX index_name_NumericFindingValue FOR (n:NumericFindingValue) ON (n.name)',
        'CREATE INDEX index_name_EventValue FOR (n:EventValue) ON (n.name)',
        'CREATE INDEX index_name_TextualFindingValue FOR (n:TextualFindingValue) ON (n.name)',
        'CREATE INDEX index_name_LagTimeValue FOR (n:LagTimeValue) ON (n.name)',
        'CREATE INDEX index_name_NumericValue FOR (n:NumericValue) ON (n.name)',
        'CREATE INDEX index_name_SimpleConceptValue FOR (n:SimpleConceptValue) ON (n.name)',
        'CREATE INDEX index_name_NumericValueWithUnitValue FOR (n:NumericValueWithUnitValue) ON (n.name)',
        'CREATE INDEX index_name_CompoundValue FOR (n:CompoundValue) ON (n.name)',
        'CREATE INDEX index_name_CompoundAliasValue FOR (n:CompoundAliasValue) ON (n.name)',
        'CREATE INDEX index_name_OdmVendorNamespaceValue FOR (n:OdmVendorNamespaceValue) ON (n.name)',
        'CREATE INDEX index_name_OdmVendorAttributeValue FOR (n:OdmVendorAttributeValue) ON (n.name)',
        'CREATE INDEX index_name_OdmTemplateValue FOR (n:OdmTemplateValue) ON (n.name)',
        'CREATE INDEX index_name_OdmDescriptionValue FOR (n:OdmDescriptionValue) ON (n.name)',
        'CREATE INDEX index_name_OdmFormValue FOR (n:OdmFormValue) ON (n.name)',
        'CREATE INDEX index_name_OdmItemGroupValue FOR (n:OdmItemGroupValue) ON (n.name)',
        'CREATE INDEX index_name_OdmItemValue FOR (n:OdmItemValue) ON (n.name)',
        'CREATE INDEX index_name_OdmAliasValue FOR (n:OdmAliasValue) ON (n.name)',
        'CREATE INDEX index_name_ObjectiveTemplateValue FOR (n:ObjectiveTemplateValue) ON (n.name)',
        'CREATE INDEX index_name_ObjectiveValue FOR (n:ObjectiveValue) ON (n.name)',
        'CREATE INDEX index_name_EndpointTemplateValue FOR (n:EndpointTemplateValue) ON (n.name)',
        'CREATE INDEX index_name_EndpointValue FOR (n:EndpointValue) ON (n.name)',
        'CREATE INDEX index_name_TimeframeTemplateValue FOR (n:TimeframeTemplateValue) ON (n.name)',
        'CREATE INDEX index_name_TimeframeValue FOR (n:TimeframeValue) ON (n.name)',
        'CREATE INDEX index_name_StudyDayValue FOR (n:StudyDayValue) ON (n.name)',
        'CREATE INDEX index_name_StudyDurationDaysValue FOR (n:StudyDurationDaysValue) ON (n.name)',
        'CREATE INDEX index_name_StudyDurationWeeksValue FOR (n:StudyDurationWeeksValue) ON (n.name)',
        'CREATE INDEX index_name_StudyWeekValue FOR (n:StudyWeekValue) ON (n.name)',
        'CREATE INDEX index_name_VisitNameValue FOR (n:VisitNameValue) ON (n.name)',
        'CREATE INDEX index_name_CriteriaTemplateValue FOR (n:CriteriaTemplateValue) ON (n.name)',
        'CREATE INDEX index_name_TimePointValue FOR (n:TimePointValue) ON (n.name)',
        'CREATE INDEX index_name_CriteriaValue FOR (n:CriteriaValue) ON (n.name)',
        'CREATE INDEX index_name_ActivityDescriptionTemplateValue FOR (n:ActivityDescriptionTemplateValue) ON (n.name)',
