{{/*
Expand the name of the chart.
*/}}
{{- define "ap2-expense.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "ap2-expense.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "ap2-expense.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "ap2-expense.labels" -}}
helm.sh/chart: {{ include "ap2-expense.chart" . }}
{{ include "ap2-expense.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "ap2-expense.selectorLabels" -}}
app.kubernetes.io/name: {{ include "ap2-expense.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "ap2-expense.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "ap2-expense.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Backend image
*/}}
{{- define "ap2-expense.backend.image" -}}
{{- printf "%s:%s" .Values.images.backend.repository (.Values.images.backend.tag | default .Chart.AppVersion) }}
{{- end }}

{{/*
Frontend image
*/}}
{{- define "ap2-expense.frontend.image" -}}
{{- printf "%s:%s" .Values.images.frontend.repository (.Values.images.frontend.tag | default .Chart.AppVersion) }}
{{- end }}
