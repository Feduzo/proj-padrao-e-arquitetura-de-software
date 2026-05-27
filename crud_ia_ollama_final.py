"""
CRUD + IA Real com Ollama
Sistema de Previsão de Churn usando Modelo de Linguagem Local

Autor: Felipe de Sousa Duzo
RA: 202320905
Data: Maio 2026

Requisitos:
  - Ollama (baixar em https://ollama.ai)
  - Rodar: ollama run mistral no powershell
  - pip install requests
"""

import requests
import json
import time
from typing import Optional
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "mistral" 


class Cliente:
    def __init__(self, id: int, nome: str, score: int):
        if not (0 <= score <= 100):
            raise ValueError("Score deve ser 0-100")
        self.id = id
        self.nome = nome
        self.score = score
        self.risco = None  
        self.probabilidade = None
        self.tempo_ia = None

    def __repr__(self):
        return f"Cliente({self.id}, {self.nome}, score={self.score})"


class RepositorioCliente:
    def __init__(self):
        self.clientes = {}

    def criar(self, cliente: Cliente):
        if cliente.id in self.clientes:
            raise ValueError(f"Cliente {cliente.id} ja esta no sistema")
        self.clientes[cliente.id] = cliente
        return cliente

    def ler(self, id: int) -> Optional[Cliente]:
        return self.clientes.get(id)

    def atualizar(self, id: int, **kwargs):
        c = self.ler(id)
        if not c:
            raise ValueError(f"Cliente {id} nao foi encontrado" )
        for k, v in kwargs.items():
            setattr(c, k, v)
        return c

    def deletar(self, id: int):
        if id in self.clientes:
            del self.clientes[id]
            return True
        return False

    def listar(self):
        return list(self.clientes.values())


class ChurnIA:    
    def __init__(self, url=OLLAMA_URL, model=MODEL):
        self.url = url
        self.model = model
        self._check_ollama()

    def _check_ollama(self):
        try:
            r = requests.post(self.url, json={"model": self.model, "prompt": "test"}, timeout=2)
            if r.status_code != 200:
                raise ConnectionError("Não foi possível conectar no Ollama")
        except:
            print("\n erro Ollama está off")
            print("rode ollama com 'run mistral' e tente denovo")
            exit(1)

    def prever(self, score: int) -> dict:
        prompt = f"""Você é um serviço de previsão de churn.
Entrada: {{"score_atividade": {score}}}
Responda apenas em JSON com os campos: {{"probabilidade": <float 0.0-1.0>, "risco": "<ALTO|MÉDIO|BAIXO>"}}
Regras: se score < 30 => probabilidade 0.90, risco "ALTO"; 
        se 30 ≤ score < 60 => probabilidade 0.50, risco "MÉDIO"; 
        se score ≥ 60 => probabilidade 0.10, risco "BAIXO"."""

        inicio = time.time()
        
        try:
            response = requests.post(
                self.url,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=60
            )
            
            tempo = time.time() - inicio
            
            if response.status_code != 200:
                raise Exception(f"Erro : {response.status_code}")
            
            data = response.json()
            resposta_texto = data.get("response", "").strip()            

            try:
                start = resposta_texto.find('{')
                end = resposta_texto.rfind('}') + 1
                if start >= 0 and end > start:
                    json_str = resposta_texto[start:end]
                    resultado = json.loads(json_str)
                else:
                    raise ValueError("JSON nao foi encontrado")
            except json.JSONDecodeError:
                raise ValueError("Ollama nao retornou nenhum JSON valido")
            return {
                "probabilidade": float(resultado["probabilidade"]),
                "risco": resultado["risco"],
                "tempo": round(tempo, 2),
                "modelo": self.model
            }
            
        except requests.exceptions.Timeout:
            raise Exception("ollama demorou muito")
            raise Exception("ollama Timeout")
        except Exception as e:
            raise Exception(f"Ollama erro call: {str(e)}")


class SistemaCRUDIA:
    def __init__(self):
        self.repo = RepositorioCliente()
        self.ia = ChurnIA()

    def adicionar_cliente(self, id: int, nome: str, score: int):
        c = Cliente(id, nome, score)
        return self.repo.criar(c)

    def analisar_churn(self, cliente_id: int) -> dict:
        cliente = self.repo.ler(cliente_id)
        if not cliente:
            raise ValueError(f"Cliente {cliente_id} não existe")
        
        resultado_ia = self.ia.prever(cliente.score)
        
        self.repo.atualizar(
            cliente_id,
            risco=resultado_ia["risco"],
            probabilidade=resultado_ia["probabilidade"],
            tempo_ia=resultado_ia["tempo"]
        )
        
        return {
            "cliente": cliente.nome,
            "score": cliente.score,
            "risco": resultado_ia["risco"],
            "prob": resultado_ia["probabilidade"],
            "tempo_ms": resultado_ia["tempo"] * 1000,
            "modelo": resultado_ia["modelo"]
        }


# ============= Testesss =============

def test_crud_basico():
    print("\n Teste basico")
    print("-" * 60)
    
    repo = RepositorioCliente()
    c = Cliente(1, "João", 50)
    repo.criar(c)
    print("Cliente criado")
    
    lido = repo.ler(1)
    assert lido.nome == "João"
    print("Cliente lido")
    
    repo.atualizar(1, score=60)
    assert repo.ler(1).score == 60
    print("Cliente atualizado")
    
    repo.deletar(1)
    assert repo.ler(1) is None
    print("Cliente deletado")


def test_ia_com_ollama():
    print("\n Teste com Ollama")
    print("-" * 60)
    
    ia = ChurnIA()
    
    scores = [20, 45, 75]
    for score in scores:
        print(f"\n  Score {score}:")
        resultado = ia.prever(score)
        print(f"    Risco: {resultado['risco']}")
        print(f"    Probabilidade: {resultado['probabilidade']}")
        print(f"    Tempo: {resultado['tempo']}s")
        print(f"    Modelo: {resultado['modelo']}")


def test_integracao():
    print("\n Teste de CRUD + IA")
    print("-" * 60)
    
    sistema = SistemaCRUDIA()
    
    print("\n  add clientes")
    sistema.adicionar_cliente(1, "Felipe", 25)
    sistema.adicionar_cliente(2, "Juliana", 50)
    sistema.adicionar_cliente(3, "Marcella", 80)
    print("3 clientes criados")
    
    print("\n  testando churn")
    for id in [1, 2, 3]:
        resultado = sistema.analisar_churn(id)
        print(f"\n{resultado['cliente']} (score {resultado['score']})")
        print(f"Risco: {resultado['risco']}")
        print(f"Probabilidade: {resultado['prob']}")
        print(f"Tempo resposta: {resultado['tempo_ms']:.0f}ms")
    
    print("\n Checando persistencia no DB")
    felipe = sistema.repo.ler(1)
    assert felipe.risco is not None
    print(f"Felipe tem risco salvo: {felipe.risco}")


if __name__ == "__main__":
    try:
        test_crud_basico()
        test_ia_com_ollama()
        test_integracao()
        
        print("\n" + "=" * 60)
        print("Amem, todos os testes passaram")
        print("=" * 60)
        
    except Exception as e:
        print(f"erro {str(e)}")
        exit(1)