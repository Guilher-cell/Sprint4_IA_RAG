# Manual do Síndico — GoodWe EV ChargeOps

Documento didático elaborado pela equipe do EV Challenge (FIAP × GoodWe) com base no escopo do desafio. Não é um manual oficial da GoodWe; os valores são de referência para a simulação.

## 1. Visão geral do painel do síndico

O painel administrativo do EV ChargeOps concentra a gestão do carregamento compartilhado do condomínio. Nele o síndico acompanha o consumo geral e por unidade, define regras de uso e horários, configura o limite de potência simultânea e recebe alertas de falha dos carregadores. O acesso é feito pelo portal web do síndico, com login individual. O zelador pode receber um perfil técnico com acesso apenas ao diagnóstico dos carregadores.

## 2. Configuração de tarifa e regras de uso

A tarifa base (R$/kWh) é definida pelo síndico em Painel > Configurações > Tarifa. O valor de referência usado neste material é R$ 0,90 por kWh. O síndico também pode ativar a faixa econômica, uma tarifa reduzida para horários de menor demanda, como a madrugada. O valor de referência da faixa econômica é R$ 0,72 por kWh, entre 22:00 e 06:00.

As regras de uso são ajustadas em Painel > Configurações > Regras de uso: duração máxima da janela de agendamento (referência: 6 horas), antecedência mínima de reserva (referência: 2 horas) e número máximo de reservas por unidade por semana (referência: 4). Mudanças de regra valem para novos agendamentos, não alteram reservas já confirmadas.

## 3. Limite de potência simultânea

O limite de potência simultânea define quanto o quadro elétrico compartilhado pode fornecer, ao mesmo tempo, a todos os carregadores ativos. O valor de referência do condomínio simulado é 22,0 kW. O síndico altera o limite em Painel > Orquestração > Limite de potência, mas deve fazê-lo apenas com base no laudo do eletricista responsável pelo quadro, nunca por tentativa e erro. O sistema emite alerta ao síndico quando o uso passa de 80% do limite (17,6 kW no valor de referência).

## 4. Relatórios de consumo e rateio

O sistema gera automaticamente, no primeiro dia de cada mês, o relatório mensal de consumo geral e por unidade. O rateio é proporcional ao consumo em kWh registrado por unidade nos ciclos de registro RFID ou do app. Cada ciclo guarda início, fim, kWh consumido, box utilizado e unidade associada. O valor de cada unidade é o consumo em kWh multiplicado pela tarifa vigente no horário de cada ciclo. O relatório pode ser exportado em PDF ou CSV para a administradora do condomínio e é lançado na mesma cobrança da taxa condominial.

## 5. Cadastro e bloqueio de cartões RFID

Cada unidade pode ter até 3 cartões RFID cadastrados. O cadastro é feito em Painel > Usuários > Cartões, informando a unidade e o número do cartão. Em caso de perda ou roubo, o síndico bloqueia o cartão no mesmo menu e emite um novo cadastro; sessões em andamento com cartão bloqueado são encerradas no próximo ciclo de verificação. Um cartão bloqueado não consegue iniciar novas sessões em nenhum box.

## 6. Alertas e notificações

Falhas geram notificação por e-mail e no painel do síndico e do zelador. Os tipos de alerta são: erro de comunicação de um carregador, falha elétrica, cartão RFID não reconhecido repetidamente, uso de potência acima de 80% do limite e carregador ocupado após o fim da carga. O síndico escolhe quais alertas deseja receber por e-mail em Painel > Alertas. Alertas de falha elétrica e de erro de comunicação persistente devem ser encaminhados ao suporte técnico GoodWe, conforme a política de escalonamento.
