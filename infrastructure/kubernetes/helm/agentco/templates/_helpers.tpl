{{/*
Common AgentCo Helm helpers.
*/}}

{{- define "agentco.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "agentco.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{- define "agentco.labels" -}}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" }}
{{ include "agentco.selectorLabels" . }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- with .Values.global.commonLabels }}
{{ toYaml . }}
{{- end }}
{{- end -}}

{{- define "agentco.selectorLabels" -}}
app.kubernetes.io/name: {{ include "agentco.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "agentco.serviceAccountName" -}}
{{- printf "%s-app" (include "agentco.fullname" .) -}}
{{- end -}}

{{- define "agentco.configChecksum" -}}
{{- toJson .Values.backend.env -}}{{- toJson .Values.frontend.env -}}{{- .Values.backend.existingSecret -}}{{- .Values.frontend.existingSecret | default "" -}}
{{- end -}}

{{- define "agentco.postgresql.host" -}}
{{- if .Values.postgresql.enabled -}}
{{- printf "%s-postgresql" .Release.Name -}}
{{- else -}}
{{- $external := .Values.externalPostgresql | default dict -}}
{{- $external.host | default "postgresql" -}}
{{- end -}}
{{- end -}}

{{- define "agentco.redis.host" -}}
{{- if .Values.redis.enabled -}}
{{- printf "%s-redis-master" .Release.Name -}}
{{- else -}}
{{- $external := .Values.externalRedis | default dict -}}
{{- $external.host | default "redis" -}}
{{- end -}}
{{- end -}}
