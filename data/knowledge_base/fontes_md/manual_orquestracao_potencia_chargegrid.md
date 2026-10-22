# Manual de Orquestração de Potência — GoodWe ChargeGrid

Documento didático elaborado pela equipe do EV Challenge (FIAP × GoodWe) com base no escopo do desafio. Não é um manual oficial da GoodWe; os valores são de referência para a simulação.

## 1. Princípio de funcionamento

Em um condomínio os carregadores compartilham o mesmo quadro elétrico geral, e a potência total disponível é limitada. A orquestração de potência monitora a potência total do quadro em tempo real e distribui a potência disponível entre os carregadores ativos, sem ultrapassar o limite configurado pelo síndico. Isso evita sobrecarga, queda de disjuntor e falta de energia no condomínio, o que não existe em um eletroposto comercial, onde cada cliente tem sua própria sessão sem limite compartilhado.

## 2. Distribuição da potência entre carregadores

A potência disponível é dividida igualmente entre os carregadores com sessão ativa, respeitando o máximo de 7,4 kW por box. A potência mínima por sessão é 1,4 kW (6 A). Quando a divisão resultaria em menos que isso, a sessão excedente entra em fila de espera em vez de reduzir todas as sessões abaixo do mínimo. Exemplo: com limite de 22,0 kW e 2 carregadores ativos consumindo 14,0 kW, restam 8,0 kW disponíveis, e um terceiro carregador pode entrar com até 7,4 kW.

## 3. Limites e alertas

O sistema emite alerta ao síndico quando o uso atinge 80% do limite (17,6 kW para um limite de 22,0 kW). Ao chegar a 100% do limite, o orquestrador reduz gradualmente a potência das sessões ativas, começando pelas de menor prioridade, até voltar abaixo do limite. A prioridade segue as reservas: sessões com agendamento confirmado têm prioridade sobre sessões sem agendamento. O síndico pode consultar a situação em tempo real em Painel > Orquestração, que mostra limite, potência em uso, potência disponível e número de carregadores ativos.

## 4. Fila de espera

Sessões sem potência disponível entram em fila por ordem de chegada, respeitando a prioridade das reservas. O morador na fila vê o LED amarelo no box e recebe uma notificação no app quando a sessão começa. A posição na fila pode ser consultada no app.

## 5. Falha de medição e modo de segurança

Se o medidor do quadro ficar sem comunicação, o orquestrador entra em modo de segurança: limita cada sessão ao mínimo de 1,4 kW e envia alerta ao síndico e ao zelador. Se um box perde a comunicação (erro de comunicação), o orquestrador reserva 7,4 kW para ele, como se estivesse em potência máxima, até a falha ser resolvida. O modo de segurança sai automaticamente quando a medição volta ao normal.
