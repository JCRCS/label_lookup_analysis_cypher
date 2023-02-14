

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
