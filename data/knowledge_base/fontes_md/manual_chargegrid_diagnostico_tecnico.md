# Manual Técnico de Diagnóstico — Carregador GoodWe ChargeGrid

Documento didático elaborado pela equipe do EV Challenge (FIAP × GoodWe) com base no escopo do desafio. Não é um manual oficial da GoodWe; os valores são de referência para a simulação.

## 1. Indicadores luminosos (LEDs)

O carregador ChargeGrid do condomínio simulado é uma wallbox monofásica de 7,4 kW (32 A, 230 V) com leitor RFID e gateway de comunicação. O estado do box é indicado pela cor do LED: verde fixo significa disponível; azul pulsando significa carregando; amarelo fixo significa sessão limitada ou aguardando pela orquestração de potência; branco piscando significa cartão RFID não reconhecido; vermelho piscando significa erro de comunicação; vermelho fixo significa falha elétrica.

## 2. Erro de comunicação (luz vermelha piscando)

Luz vermelha piscando indica que o box perdeu a comunicação com o gateway do EV ChargeOps. Nesse estado o sistema registra o status como erro_comunicacao, não recebe leituras do box e deixa de monitorar o disjuntor daquele box. Por segurança, o orquestrador de potência passa a reservar 7,4 kW para o box com falha, como se ele estivesse na potência máxima. Causas comuns: queda do Wi-Fi ou do chip 4G do gateway, roteador desligado ou cabo de rede solto. Para verificar, confira no painel se os outros boxes estão online: se todos estão offline, o problema provável é o gateway ou a rede; se só um box está offline, o problema é local do box.

## 3. RFID não reconhecido

Quando o LED branco pisca ao aproximar o cartão, siga a ordem: 1) reaproxime o cartão do leitor, sem encostar em objetos metálicos; 2) confirme no painel se o cartão está cadastrado e não bloqueado; 3) limpe o leitor com pano seco; 4) faça a reinicialização remota do box. Se o cartão continuar não sendo reconhecido depois da reinicialização, acione o suporte técnico GoodWe.

## 4. Reinicialização remota básica

A reinicialização é feita remotamente, em Painel > Carregadores > selecionar o box > Reiniciar. Aguarde 2 minutos até o LED mudar de cor. Se o problema persistir, é permitido tentar uma segunda reinicialização após 5 minutos. A reinicialização remota não envolve nenhuma intervenção no quadro elétrico. Nunca desligue disjuntores nem abra o quadro elétrico para reiniciar um carregador.

## 5. Quando acionar o suporte técnico GoodWe

Acione o suporte técnico GoodWe quando: a falha de comunicação persistir por mais de 1 hora depois de duas reinicializações remotas; o LED estiver vermelho fixo (falha elétrica); houver cheiro de queimado, cabo danificado ou aquecimento anormal; o RFID continuar não reconhecido após a reinicialização; ou o box estiver offline e o disjuntor dele não estiver sendo monitorado. Ao abrir o chamado, informe o box, o horário em que a falha começou, a cor e o padrão do LED e as ações já tentadas.

## 6. Limites de atuação do zelador

O zelador pode consultar o painel, reiniciar carregadores remotamente, conferir cartões cadastrados e abrir chamados. O zelador não deve abrir o quadro elétrico geral, mexer em disjuntores, desmontar o carregador, tocar em fios ou ligar o carregador direto na rede. Qualquer intervenção elétrica física deve ser feita por eletricista habilitado ou pelo suporte técnico GoodWe.
