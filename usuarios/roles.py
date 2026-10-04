from rolepermissions.roles import AbstractUserRole

class Gestor (AbstractUserRole):
    available_permissions ={
        'cadastrar_produtos':True,
        'cadastrar_atendente':True,
        'cadastrar_fornecedor':True,
        'realizar_atendimento':True,
    }

class Atendente (AbstractUserRole):
    available_permissions ={
        'cadastrar_produtos':True,
        'cadastrar_atendente':False,
        'cadastrar_fornecedor':False,
        'realizar_atendimento':True,

    }   
